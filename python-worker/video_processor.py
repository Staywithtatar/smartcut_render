import ffmpeg
import os
import logging
from pathlib import Path
from typing import List, Dict, Optional
import math

logger = logging.getLogger(__name__)

class ProcessingOptions:
    def __init__(
        self,
        subtitle_style: str = "professional",
        color_grading: str = "vibrant",
        enable_zoom: bool = True,
        enable_transitions: bool = True,
        aspect_ratio_strategy: str = "center_crop" # center_crop or blur_background
    ):
        self.subtitle_style = subtitle_style
        self.color_grading = color_grading
        self.enable_zoom = enable_zoom
        self.enable_transitions = enable_transitions
        self.aspect_ratio_strategy = aspect_ratio_strategy

class VideoProcessor:
    def __init__(self, input_path: str, output_path: str, options: ProcessingOptions):
        self.input_path = Path(input_path)
        self.output_path = Path(output_path)
        self.options = options
        self.temp_dir = self.input_path.parent.parent / "processing"
        self.temp_dir.mkdir(exist_ok=True)
        
        # Get video info
        try:
            probe = ffmpeg.probe(str(self.input_path))
            video_info = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            self.width = int(video_info['width'])
            self.height = int(video_info['height'])
            self.duration = float(video_info['duration'])
        except Exception as e:
            logger.error(f"Error probing video: {e}")
            raise

    def format_time_ass(self, seconds: float) -> str:
        """Format time for ASS subtitles (H:MM:SS.cs)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds * 100) % 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"

    def create_ass(self, subtitles: List[Dict], keywords: List[str] = None) -> Path:
        """Create Advanced Substation Alpha subtitle file with Pro styling"""
        ass_path = self.temp_dir / "subtitles.ass"
        
        # Calculate font size based on video height (approx 4-5% of height)
        font_size = int(self.height * 0.045)
        # Calculate bottom margin (approx 15-20% from bottom)
        margin_v = int(self.height * 0.15)
        
        # Define styles (Hormozi-like)
        # PlayResX/Y matches video resolution for consistent scaling
        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {self.width}
PlayResY: {self.height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Kanit ExtraBold,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,10,10,{margin_v},1
Style: Keyword,Kanit ExtraBold,{int(font_size*1.1)},&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,105,105,0,0,1,5,3,2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(header)
            
            for sub in subtitles:
                start = self.format_time_ass(sub['start'])
                end = self.format_time_ass(sub['end'])
                text = sub['text']
                
                # Check for keywords to highlight
                style = "Default"
                if keywords:
                    for keyword in keywords:
                        if keyword in text:
                            # Highlight keyword with color (Yellow: &H0000FFFF in BGR)
                            # Note: ASS uses BGR, so Yellow is 00FFFF
                            text = text.replace(keyword, f"{{\\c&H00FFFF&}}{keyword}{{\\c&HFFFFFF&}}")
                            # Or switch to Keyword style for the whole line if it's short
                            # style = "Keyword" 
                
                f.write(f"Dialogue: 0,{start},{end},{style},,0,0,0,,{text}\n")
                
        return ass_path

    def apply_jump_cuts(self, jump_cuts: List[Dict]) -> str:
        """Remove silent/unwanted parts"""
        if not jump_cuts:
            return str(self.input_path)
            
        output_file = self.temp_dir / "jump_cut_output.mp4"
        
        # Calculate keep segments
        keep_segments = []
        current_time = 0.0
        
        sorted_cuts = sorted(jump_cuts, key=lambda x: x['start'])
        
        for cut in sorted_cuts:
            start = cut['start']
            end = cut['end']
            
            if start > current_time:
                keep_segments.append((current_time, start))
            
            current_time = max(current_time, end)
            
        if current_time < self.duration:
            keep_segments.append((current_time, self.duration))
            
        # Create filter complex
        segments = []
        for start, end in keep_segments:
            segments.append(f"between(t,{start},{end})")
            
        select_expr = "+".join(segments)
        
        try:
            (
                ffmpeg
                .input(str(self.input_path))
                .output(
                    str(output_file),
                    vf=f"select='{select_expr}',setpts=N/FRAME_RATE/TB",
                    af=f"aselect='{select_expr}',asetpts=N/SR/TB",
                    loglevel='error'
                )
                .overwrite_output()
                .run()
            )
            return str(output_file)
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error applying jump cuts: {e.stderr.decode() if e.stderr else str(e)}")
            raise

    def add_color_grading(self, video_path: str, style: str = "vibrant") -> str:
        """Apply color grading"""
        output_file = self.temp_dir / "graded_output.mp4"
        
        # Define presets
        presets = {
            "vibrant": "eq=contrast=1.1:saturation=1.3,curves=preset=strong_contrast",
            "cinematic": "eq=contrast=1.1:saturation=0.9,colorbalance=rs=0.05:bs=-0.05",
            "natural": "eq=saturation=1.1"
        }
        
        filter_str = presets.get(style, presets["vibrant"])
        
        try:
            (
                ffmpeg
                .input(video_path)
                .output(str(output_file), vf=filter_str, acodec='copy', loglevel='error')
                .overwrite_output()
                .run()
            )
            return str(output_file)
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error applying color grading: {e.stderr.decode() if e.stderr else str(e)}")
            raise

    def add_subtitles(self, subtitles: List[Dict], video_path: str, keywords: List[str] = None) -> str:
        """Add subtitles using ASS format"""
        output_file = self.temp_dir / "subtitled_output.mp4"
        
        try:
            ass_path = self.create_ass(subtitles, keywords)
            
            # Use proper path formatting for Windows
            ass_path_str = str(ass_path).replace('\\', '/').replace(':', '\\:')
            
            (
                ffmpeg
                .input(video_path)
                .output(
                    str(output_file),
                    vf=f"ass='{ass_path_str}'",
                    acodec='copy',
                    loglevel='error'
                )
                .overwrite_output()
                .run()
            )
            return str(output_file)
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error adding subtitles: {e.stderr.decode() if e.stderr else str(e)}")
            raise

    def add_zoom_effects(self, video_path: str, highlights: List[Dict]) -> str:
        """Add dynamic zoom effects"""
        if not self.options.enable_zoom or not highlights:
            return video_path
            
        output_file = self.temp_dir / "zoomed_output.mp4"
        
        # Simple zoom logic: Zoom in 1.15x over 0.5s at start of highlight
        # Using zoompan filter
        # Note: This is a simplified implementation. Complex zoompan can be tricky.
        # We'll use a basic "punch in" effect for now.
        
        # Construct zoompan expression
        # Default: zoom=1
        # Highlight: zoom=1.15
        
        # We need to chain filters for multiple highlights, which is complex.
        # Instead, we'll apply a generic "active camera" effect if there are highlights
        # Or just one simple zoom for demonstration.
        
        # Let's try a simple approach: Zoom in slightly on ALL highlights
        # zoompan=z='if(between(t,start,end),1.15,1)':d=1
        
        conditions = []
        for h in highlights:
            start = h['start']
            end = h['end']
            conditions.append(f"between(t,{start},{end})")
            
        if not conditions:
            return video_path
            
        # Simple approach: Apply zoom to entire video when highlights exist
        # More sophisticated per-segment zoom would require complex filter_complex
        
        try:
            # Use a simple constant zoom for now (1.1x slight zoom)
            # This avoids complex expression parsing issues
            (
                ffmpeg
                .input(video_path)
                .output(
                    str(output_file),
                    vf="zoompan=z='1.1':d=1:fps=30",
                    acodec='copy',
                    loglevel='error'
                )
                .overwrite_output()
                .run()
            )
            return str(output_file)
        except ffmpeg.Error as e:
            logger.warning(f"Zoom effect failed, skipping: {e}")
            return video_path

    def convert_aspect_ratio(self, video_path: str) -> str:
        """Convert to 9:16 using Center Crop or Blur Background"""
        output_file = self.output_path
        
        try:
            if self.options.aspect_ratio_strategy == "center_crop":
                # Center Crop Strategy (Pro)
                # 1. Scale height to 1920 (maintaining aspect ratio)
                # 2. Crop to 1080x1920 (center)
                
                # Check current aspect ratio
                current_ar = self.width / self.height
                target_ar = 9 / 16
                
                if current_ar > target_ar:
                    # Video is wider than target (e.g. 16:9 source -> 9:16 target)
                    # Scale height to 1920, width will be > 1080
                    vf_filter = 'scale=-1:1920,crop=1080:1920'
                else:
                    # Video is taller/narrower (unlikely for horizontal source)
                    # Scale width to 1080, height will be > 1920
                    vf_filter = 'scale=1080:-1,crop=1080:1920'
                
                # Use simple output with vf and acodec copy
                (
                    ffmpeg
                    .input(video_path)
                    .output(str(output_file), vf=vf_filter, acodec='copy', loglevel='error')
                    .overwrite_output()
                    .run()
                )
                
            else:
                # Blur Background Strategy (Old School)
                # Need to use filter_complex to properly handle audio
                input_stream = ffmpeg.input(video_path)
                
                # Background: Scale to fill -> Boxblur
                bg = (
                    input_stream
                    .filter('scale', 1080, 1920)
                    .filter('boxblur', luma_radius='min(h,w)/20', luma_power=1)
                    .filter('setsar', 1)
                )
                
                # Foreground: Scale to fit width
                fg = (
                    input_stream
                    .filter('scale', 1080, -1)
                )
                
                # Overlay video
                overlayed = ffmpeg.overlay(bg, fg, x='(W-w)/2', y='(H-h)/2')
                
                # Output with audio from original input
                output = ffmpeg.output(
                    overlayed, 
                    input_stream.audio,
                    str(output_file), 
                    loglevel='error'
                )
                ffmpeg.run(output, overwrite_output=True)
                
            return str(output_file)
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error converting aspect ratio: {e.stderr.decode() if e.stderr else str(e)}")
            raise
