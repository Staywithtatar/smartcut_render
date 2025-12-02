# Effects Processor - AI-driven visual effects

import ffmpeg
import logging
from pathlib import Path
from typing import List
from ai_models import Highlight, Transition, AIEditingScript

logger = logging.getLogger(__name__)

class EffectsProcessor:
    """Apply AI-determined visual effects"""
    
    def __init__(self, script: AIEditingScript, temp_dir: Path, video_info: dict):
        self.script = script
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.width = video_info['width']
        self.height = video_info['height']
    
    def apply_highlights(self, video_path: Path, highlights: List[Highlight]) -> Path:
        """Apply AI-determined effects to highlights (zoom, blur, slow-motion)"""
        if not highlights:
            return video_path
        
        output = self.temp_dir / "05_highlights.mp4"
        
        logger.info(f"Applying effects to {len(highlights)} highlights")
        
        # Process zoom effects
        zoom_highlights = [h for h in highlights if h.effects.zoom]
        if zoom_highlights:
            video_path = self._apply_zoom_effects(video_path, zoom_highlights)
        
        # Process blur effects
        blur_highlights = [h for h in highlights if h.effects.blur]
        if blur_highlights:
            video_path = self._apply_blur_effects(video_path, blur_highlights)
        
        return video_path
    
    def _apply_zoom_effects(self, video_path: Path, highlights: List[Highlight]) -> Path:
        """Apply dynamic zoom with AI-determined intensity and easing"""
        output = self.temp_dir / "05a_zoomed.mp4"
        
        logger.info(f"Applying zoom to {len(highlights)} segments")
        
        # Build simple zoom conditions
        # Zoom IN during highlights, zoom OUT (1.0) otherwise
        zoom_parts = []
        
        for highlight in highlights:
            start = highlight.start
            end = highlight.end
            
            # Skip if no zoom config
            if not highlight.effects or not highlight.effects.zoom:
                logger.warning(f"Highlight at {start}-{end}s has no zoom config, skipping")
                continue
                
            zoom_config = highlight.effects.zoom
            
            # Get zoom factor
            zoom_factor = self.script.get_zoom_factor(zoom_config.intensity)
            
            # Simple condition: if in this highlight, zoom to factor, else 1.0
            zoom_parts.append(f"if(between(t,{start},{end}),{zoom_factor},1)")
        
        # Combine with max() to handle overlaps
        # FFmpeg max() takes only 2 arguments, so we must chain them: max(a, max(b, c))
        if not zoom_parts:
            final_zoom = "1"
        elif len(zoom_parts) == 1:
            final_zoom = zoom_parts[0]
        else:
            # Recursive max construction
            final_zoom = zoom_parts[0]
            for part in zoom_parts[1:]:
                final_zoom = f"max({final_zoom},{part})"
        
        # Determine zoom center based on orientation
        is_vertical = self.height > self.width
        
        if is_vertical:
            # Vertical: Focus on upper part (faces usually) - 35% from top
            center_x = "iw/2-(iw/zoom/2)"
            center_y = "ih*0.35-(ih/zoom/2)"
            logger.info("Vertical video detected: Zooming to upper-center")
        else:
            # Horizontal: Focus on center
            center_x = "iw/2-(iw/zoom/2)"
            center_y = "ih/2-(ih/zoom/2)"
            logger.info("Horizontal video detected: Zooming to center")
        
        # Debug logging
        logger.info(f"Zoom parts ({len(zoom_parts)}): {zoom_parts}")
        logger.info(f"Final zoom expression: {final_zoom}")
        
        try:
            # Use filter() method to avoid quote escaping issues
            # Split audio and video to preserve audio
            input_stream = ffmpeg.input(str(video_path))
            video = input_stream.video.filter('zoompan', z=final_zoom, x=center_x, y=center_y, d=1, fps=30)
            audio = input_stream.audio
            
            (
                ffmpeg
                .output(video, audio, str(output), acodec='copy', loglevel='error')
                .overwrite_output()
                .run()
            )
            logger.info(f"✅ Zoom effects applied to {len(highlights)} segments")
            return output
        except ffmpeg.Error as e:
            logger.warning(f"Zoom effects failed: {e}")
            logger.warning(f"Zoom expression was: z={final_zoom}, x={center_x}, y={center_y}")
            return video_path
    
    def _apply_blur_effects(self, video_path: Path, highlights: List[Highlight]) -> Path:
        """Apply selective blur effects"""
        output = self.temp_dir / "05b_blurred.mp4"
        
        logger.info(f"Applying blur to {len(highlights)} segments")
        
        # Build blur filter with enable expressions
        blur_filters = []
        for highlight in highlights:
            start = highlight.start
            end = highlight.end
            blur_config = highlight.effects.blur
            
            # Calculate blur radius from intensity (0-100 -> 0-20)
            radius = int(blur_config.intensity / 5)
            
            if blur_config.type == 'background':
                # Background blur (would need complex filter_complex for selective blur)
                # For now, apply simple blur to entire frame
                blur_filters.append(
                    f"boxblur=luma_radius={radius}:enable='between(t,{start},{end})'"
                )
            else:
                # Edge blur
                blur_filters.append(
                    f"boxblur=luma_radius={radius//2}:enable='between(t,{start},{end})'"
                )
        
        if blur_filters:
            vf = ','.join(blur_filters)
            try:
                (
                    ffmpeg
                    .input(str(video_path))
                    .output(str(output), vf=vf, acodec='copy', loglevel='error')
                    .overwrite_output()
                    .run()
                )
                logger.info(f"✅ Blur effects applied to {len(highlights)} segments")
                return output
            except ffmpeg.Error as e:
                logger.warning(f"Blur effects failed: {e}")
                return video_path
        
        return video_path
    
    def apply_transitions(self, video_path: Path, transitions: List[Transition]) -> Path:
        """Apply AI-determined transitions between scenes"""
        if not transitions:
            return video_path
        
        output = self.temp_dir / "06_transitions.mp4"
        
        logger.info(f"Applying {len(transitions)} transitions")
        
        # Note: Transitions are complex in FFmpeg
        # For now, we'll skip or implement simple fades
        # Full implementation would use xfade filter
        
        logger.info("⚠️  Transitions not yet implemented")
        return video_path
