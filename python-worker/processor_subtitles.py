# Subtitle Processor - AI-driven subtitle generation

import ffmpeg
import logging
from pathlib import Path
from ai_models import SubtitleConfig

logger = logging.getLogger(__name__)

class SubtitleProcessor:
    """Generate and apply AI-styled subtitles"""
    
    def __init__(self, subtitle_config: SubtitleConfig, temp_dir: Path, video_info: dict):
        self.config = subtitle_config
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.width = video_info['width']
        self.height = video_info['height']
    
    def add_subtitles(self, video_path: Path) -> Path:
        """Add AI-styled subtitles with keyword highlighting"""
        if not self.config.segments:
            return video_path
        
        output = self.temp_dir / "08_subtitled.mp4"
        
        logger.info(f"Adding {len(self.config.segments)} subtitle segments")
        
        # Create ASS file
        ass_path = self._create_ass_file()
        
        try:
            # Use filename parameter (not positional) for Windows compatibility
            subtitle_file = str(ass_path)
            logger.info(f"Applying subtitles from: {subtitle_file}")
            
            # Split audio and video to preserve audio
            input_stream = ffmpeg.input(str(video_path))
            video = input_stream.video.filter('subtitles', filename=subtitle_file)
            audio = input_stream.audio
            
            (
                ffmpeg
                .output(video, audio, str(output), acodec='copy', loglevel='error')
                .overwrite_output()
                .run()
            )
            logger.info(f"✅ Subtitles added ({len(self.config.segments)} segments)")
            return output
        except ffmpeg.Error as e:
            logger.error(f"Subtitle application failed: {e}")
            logger.error(f"Subtitle file exists: {ass_path.exists()}")
            return video_path
    
    def _create_ass_file(self) -> Path:
        """Create ASS subtitle file with AI styling"""
        ass_path = self.temp_dir / "subtitles.ass"
        
        # Calculate dynamic sizing based on video resolution
        # Base size on 1080p height (1920x1080 or 1080x1920)
        ref_height = 1920 if self.height > self.width else 1080
        scale_factor = self.height / ref_height
        
        # Standard size is ~4.5% of height for 9:16, ~3.5% for 16:9
        base_pct = 0.045 if self.height > self.width else 0.035
        
        font_size = int(self.height * base_pct) if self.config.style.size == 'auto' else self.config.style.size
        
        # Adjust margin based on orientation (Vertical needs more space for UI)
        is_vertical = self.height > self.width
        margin_pct = 0.20 if is_vertical else 0.10
        margin_v = int(self.height * margin_pct)
        
        logger.info(f"Subtitle config: Font={font_size}px, Margin={margin_v}px (Vertical={is_vertical})")
        
        # Position mapping
        alignment_map = {
            'top': 8,
            'center': 5,
            'bottom': 2
        }
        alignment = alignment_map[self.config.style.position]
        
        # Color conversion (white = &H00FFFFFF in BGR)
        color = '&H00FFFFFF'  # Default white
        
        # ASS header
        # ASS header (Must not have indentation!)
        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {self.width}
PlayResY: {self.height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.config.style.font},{font_size},{color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,{alignment},10,10,{margin_v},1
Style: Keyword,{self.config.style.font},{int(font_size*1.1)},&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,105,105,0,0,1,5,3,{alignment},10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        with open(ass_path, 'w', encoding='utf-8') as f:
            f.write(header)
            
            for segment in self.config.segments:
                start = self._format_time_ass(segment.start)
                end = self._format_time_ass(segment.end)
                text = segment.text.replace('\n', ' ').replace('\r', '')
                # Sanitize text for ASS (remove commas if they break parsing, though usually fine in text field)
                # But definitely handle newlines which break the ASS line structure
                
                # Highlight keywords
                if self.config.keywords:
                    for keyword in self.config.keywords:
                        if keyword in text:
                            # Yellow highlight
                            text = text.replace(
                                keyword,
                                f"{{\\c&H00FFFF&}}{keyword}{{\\c&HFFFFFF&}}"
                            )
                
                f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")
        
        return ass_path
    
    def _format_time_ass(self, seconds: float) -> str:
        """Format time for ASS subtitles (H:MM:SS.cs)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        centisecs = int((seconds * 100) % 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"
