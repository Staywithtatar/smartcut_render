# Audio Processor - AI-driven audio processing

import ffmpeg
import logging
from pathlib import Path
from typing import List
from ai_models import AudioConfig, AudioSegment

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Process audio based on AI instructions"""
    
    def __init__(self, audio_config: AudioConfig, temp_dir: Path):
        self.config = audio_config
        self.temp_dir = temp_dir
        self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def normalize(self, video_path: Path) -> Path:
        """Normalize audio loudness (EBU R128)"""
        if not self.config.normalization.enabled:
            return video_path
        
        output = self.temp_dir / "01_normalized_audio.mp4"
        target_loudness = self.config.normalization.targetLoudness
        
        logger.info(f"Normalizing audio to {target_loudness} LUFS")
        
        try:
            (
                ffmpeg
                .input(str(video_path))
                .output(
                    str(output),
                    af=f'loudnorm=I={target_loudness}:TP=-1.5:LRA=11',
                    vcodec='copy',
                    loglevel='error'
                )
                .overwrite_output()
                .run()
            )
            logger.info("✅ Audio normalization complete")
            return output
        except ffmpeg.Error as e:
            logger.error(f"Audio normalization failed: {e}")
            return video_path
    
    def apply_dynamic_adjustments(self, video_path: Path, segments: List[AudioSegment]) -> Path:
        """Apply AI-determined volume adjustments to specific segments"""
        if not segments:
            return video_path
        
        output = self.temp_dir / "02_adjusted_audio.mp4"
        
        logger.info(f"Applying {len(segments)} audio adjustments")
        
        # Build volume filter expressions
        volume_filters = []
        for segment in segments:
            start = segment.start
            end = segment.end
            action = segment.action
            intensity = segment.intensity
            
            if action == 'boost':
                volume = 1 + intensity
            elif action == 'reduce':
                volume = 1 - (intensity * 0.5)  # Max 50% reduction
            elif action == 'denoise':
                # Use afftdn filter for noise reduction
                continue
            else:
                continue
            
            volume_filters.append(
                f"volume={volume}:enable='between(t,{start},{end})'"
            )
        
        if volume_filters:
            af = ','.join(volume_filters)
            try:
                (
                    ffmpeg
                    .input(str(video_path))
                    .output(str(output), af=af, vcodec='copy', loglevel='error')
                    .overwrite_output()
                    .run()
                )
                logger.info("✅ Audio adjustments complete")
                return output
            except ffmpeg.Error as e:
                logger.error(f"Audio adjustment failed: {e}")
                return video_path
        
        return video_path
    
    def denoise(self, video_path: Path) -> Path:
        """Remove background noise"""
        output = self.temp_dir / "03_denoised_audio.mp4"
        
        logger.info("Removing background noise")
        
        try:
            (
                ffmpeg
                .input(str(video_path))
                .output(
                    str(output),
                    af='afftdn=nf=-25',  # Noise floor -25dB
                    vcodec='copy',
                    loglevel='error'
                )
                .overwrite_output()
                .run()
            )
            logger.info("✅ Noise reduction complete")
            return output
        except ffmpeg.Error as e:
            logger.error(f"Noise reduction failed: {e}")
            return video_path
