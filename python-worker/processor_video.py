# Video Processor - AI-driven video processing

import ffmpeg
import logging
from pathlib import Path
from typing import List
from ai_models import JumpCut, VisualConfig, AspectRatio

logger = logging.getLogger(__name__)

class VideoProcessor:
    """Process video based on AI instructions"""
    
    def __init__(self, visual_config: VisualConfig, temp_dir: Path, video_info: dict):
        self.config = visual_config
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.width = video_info['width']
        self.height = video_info['height']
        self.duration = video_info['duration']
    
    def apply_jump_cuts(self, video_path: Path, cuts: List[JumpCut]) -> Path:
        """Remove unwanted segments (AI-determined jump cuts)"""
        if not cuts:
            logger.info("No jump cuts to apply")
            return video_path
        
        output = self.temp_dir / "04_jump_cuts.mp4"
        
        logger.info(f"Applying {len(cuts)} jump cuts")
        
        # Calculate segments to keep
        keep_segments = []
        current_time = 0.0
        
        sorted_cuts = sorted(cuts, key=lambda x: x.start)
        
        for cut in sorted_cuts:
            if cut.start > current_time:
                keep_segments.append((current_time, cut.start))
            current_time = max(current_time, cut.end)
        
        if current_time < self.duration:
            keep_segments.append((current_time, self.duration))
        
        logger.info(f"Keeping {len(keep_segments)} segments: {keep_segments}")
        
        # If only one segment, just trim
        if len(keep_segments) == 1:
            start, end = keep_segments[0]
            try:
                (
                    ffmpeg
                    .input(str(video_path), ss=start, t=end-start)
                    .output(str(output), c='copy', loglevel='error')
                    .overwrite_output()
                    .run()
                )
                logger.info(f"Trimmed to {start}-{end}s")
                return output
            except ffmpeg.Error as e:
                logger.error(f"Trim failed: {e}")
                return video_path
        
        # Multiple segments - use concat
        # Create segment files with RE-ENCODE (not copy) to ensure A/V sync
        segment_files = []
        for i, (start, end) in enumerate(keep_segments):
            segment_file = self.temp_dir / f"segment_{i}.mp4"
            try:
                (
                    ffmpeg
                    .input(str(video_path), ss=start, t=end-start)
                    .output(
                        str(segment_file), 
                        vcodec='libx264',
                        acodec='aac',
                        preset='fast',
                        crf=18,
                        loglevel='error'
                    )
                    .overwrite_output()
                    .run()
                )
                segment_files.append(segment_file)
                logger.info(f"Created segment {i}: {start:.2f}-{end:.2f}s")
            except ffmpeg.Error as e:
                logger.error(f"Segment {i} failed: {e}")
                return video_path
        
        # Concat segments
        if segment_files:
            try:
                # Create concat file list
                concat_file = self.temp_dir / "concat_list.txt"
                with open(concat_file, 'w') as f:
                    for seg in segment_files:
                        f.write(f"file '{seg.absolute()}'\n")
                
                # Concat with re-encode for perfect sync
                (
                    ffmpeg
                    .input(str(concat_file), format='concat', safe=0)
                    .output(
                        str(output),
                        vcodec='libx264',
                        acodec='aac',
                        preset='fast',
                        crf=18,
                        loglevel='error'
                    )
                    .overwrite_output()
                    .run()
                )
                
                # Cleanup segment files
                for seg in segment_files:
                    seg.unlink()
                concat_file.unlink()
                
                logger.info(f"✅ Jump cuts applied ({len(cuts)} segments removed)")
                return output
            except ffmpeg.Error as e:
                logger.error(f"Concat failed: {e}")
                return video_path
        
        return video_path
    
    def apply_color_grading(self, video_path: Path) -> Path:
        """Apply AI-determined color grading"""
        output = self.temp_dir / "07_color_graded.mp4"
        
        preset = self.config.colorGrading.preset
        logger.info(f"Applying {preset} color grading")
        
        # Presets
        presets = {
            'vibrant': 'eq=contrast=1.1:saturation=1.3,curves=preset=strong_contrast',
            'cinematic': 'eq=contrast=1.1:saturation=0.9,colorbalance=rs=0.05:bs=-0.05',
            'natural': 'eq=saturation=1.1',
            'custom': self._build_custom_grading()
        }
        
        vf = presets.get(preset, presets['vibrant'])
        
        try:
            (
                ffmpeg
                .input(str(video_path))
                .output(str(output), vf=vf, acodec='copy', loglevel='error')
                .overwrite_output()
                .run()
            )
            logger.info("✅ Color grading applied")
            return output
        except ffmpeg.Error as e:
            logger.error(f"Color grading failed: {e}")
            return video_path
    
    def convert_aspect_ratio(self, video_path: Path) -> Path:
        """Convert to target aspect ratio (Orientation Aware)"""
        output = self.temp_dir / "09_final_output.mp4"
        
        # Detect input orientation
        is_vertical = self.height > self.width
        
        # Determine target based on input (Smart Mode)
        if is_vertical:
            target_width, target_height = 1080, 1920
            logger.info(f"Detected Vertical Video ({self.width}x{self.height}) -> Target 9:16")
        else:
            target_width, target_height = 1920, 1080
            logger.info(f"Detected Horizontal Video ({self.width}x{self.height}) -> Target 16:9")
            
        # Calculate scaling/cropping
        current_ar = self.width / self.height
        target_ar = target_width / target_height
        
        if abs(current_ar - target_ar) < 0.01:
            # Aspect ratio matches, just scale if needed
            vf = f'scale={target_width}:{target_height}'
        else:
            # Center crop strategy
            if current_ar > target_ar:
                # Video is wider than target - scale height, crop width
                vf = f'scale=-1:{target_height},crop={target_width}:{target_height}'
            else:
                # Video is taller than target - scale width, crop height
                vf = f'scale={target_width}:-1,crop={target_width}:{target_height}'
        
        try:
            (
                ffmpeg
                .input(str(video_path))
                .output(str(output), vf=vf, acodec='copy', loglevel='error')
                .overwrite_output()
                .run()
            )
            logger.info(f"✅ Converted to {target_width}x{target_height}")
            return output
        except ffmpeg.Error as e:
            logger.error(f"Aspect ratio conversion failed: {e}")
            return video_path
    
    def _build_custom_grading(self) -> str:
        """Build custom color grading filter"""
        params = self.config.colorGrading.customParams or {}
        
        contrast = params.get('contrast', 1.0)
        saturation = params.get('saturation', 1.0)
        brightness = params.get('brightness', 0.0)
        
        return f'eq=contrast={contrast}:saturation={saturation}:brightness={brightness}'
