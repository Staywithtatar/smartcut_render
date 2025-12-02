# Main Processing Pipeline - AI-Driven Video Editor

import ffmpeg
import logging
from pathlib import Path
from ai_models import AIEditingScript
from processor_audio import AudioProcessor
from processor_video import VideoProcessor
from processor_effects import EffectsProcessor
from processor_subtitles import SubtitleProcessor

logger = logging.getLogger(__name__)

class ProcessingPipeline:
    """Orchestrate AI-driven video processing"""
    
    def __init__(self, input_path: Path, output_path: Path, script: AIEditingScript):
        self.input_path = input_path
        self.output_path = output_path
        self.script = script
        self.temp_dir = input_path.parent.parent / "processing"
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        
        # Get video info
        self.video_info = self._get_video_info()
        
        # Initialize processors
        self.audio_processor = AudioProcessor(script.audio, self.temp_dir)
        self.video_processor = VideoProcessor(script.visual, self.temp_dir, self.video_info)
        self.effects_processor = EffectsProcessor(script, self.temp_dir, self.video_info)
        self.subtitle_processor = SubtitleProcessor(script.subtitles, self.temp_dir, self.video_info)
        
        logger.info(f"Pipeline initialized for job: {script.job_id}")
        logger.info(f"Content type: {script.metadata.contentType}, Mood: {script.metadata.mood}")
    
    def execute(self) -> Path:
        """Execute full AI-driven processing pipeline"""
        current_video = self.input_path
        
        logger.info("=" * 60)
        logger.info("🎬 Starting AI-Driven Video Processing")
        logger.info("=" * 60)
        
        # Step 1: Audio Normalization (FIRST - ensures consistent audio)
        logger.info("\n[Step 1/9] Audio Normalization")
        current_video = self.audio_processor.normalize(current_video)
        
        # Step 2: Dynamic Audio Adjustments
        if self.script.audio.segments:
            logger.info(f"\n[Step 2/9] Dynamic Audio Adjustments ({len(self.script.audio.segments)} segments)")
            current_video = self.audio_processor.apply_dynamic_adjustments(
                current_video,
                self.script.audio.segments
            )
        else:
            logger.info("\n[Step 2/9] Dynamic Audio Adjustments (skipped)")
        
        # Step 3: Jump Cuts (remove unwanted segments)
        if self.script.timeline.cuts:
            logger.info(f"\n[Step 3/9] Jump Cuts ({len(self.script.timeline.cuts)} cuts)")
            current_video = self.video_processor.apply_jump_cuts(
                current_video,
                self.script.timeline.cuts
            )
            
            # IMPORTANT: Adjust subtitle timestamps after jump cuts
            # When we remove segments, subtitle timings need to shift
            if self.script.subtitles.segments:
                logger.info("Adjusting subtitle timestamps after jump cuts...")
                self._adjust_subtitle_timestamps_after_cuts()
        else:
            logger.info("\n[Step 3/9] Jump Cuts (skipped)")
        
        # Step 4: Highlight Effects (zoom, blur, slow-motion)
        if self.script.timeline.highlights:
            logger.info(f"\n[Step 4/9] Highlight Effects ({len(self.script.timeline.highlights)} highlights)")
            current_video = self.effects_processor.apply_highlights(
                current_video,
                self.script.timeline.highlights
            )
        else:
            logger.info("\n[Step 4/9] Highlight Effects (skipped)")
        
        # Step 5: Transitions
        if self.script.timeline.transitions:
            logger.info(f"\n[Step 5/9] Transitions ({len(self.script.timeline.transitions)} transitions)")
            current_video = self.effects_processor.apply_transitions(
                current_video,
                self.script.timeline.transitions
            )
        else:
            logger.info("\n[Step 5/9] Transitions (skipped)")
        
        # Step 6: Color Grading
        logger.info(f"\n[Step 6/9] Color Grading ({self.script.visual.colorGrading.preset})")
        current_video = self.video_processor.apply_color_grading(current_video)
        
        # Step 7: Aspect Ratio Conversion (BEFORE subtitles!)
        logger.info(f"\n[Step 7/9] Aspect Ratio ({self.script.visual.aspectRatio.target}, {self.script.visual.aspectRatio.strategy})")
        current_video = self.video_processor.convert_aspect_ratio(current_video)
        
        # Step 8: Subtitles (AFTER everything else to ensure perfect sync)
        if self.script.subtitles.segments:
            logger.info(f"\n[Step 8/9] Subtitles ({len(self.script.subtitles.segments)} segments)")
            current_video = self.subtitle_processor.add_subtitles(current_video)
        else:
            logger.info("\n[Step 8/9] Subtitles (skipped)")
        
        # Step 9: Copy to final output
        logger.info("\n[Step 9/9] Finalizing")
        if current_video != self.output_path:
            import shutil
            shutil.copy2(current_video, self.output_path)
            logger.info(f"✅ Final video: {self.output_path}")
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 Processing Complete!")
        logger.info("=" * 60)
        
        return self.output_path
    
    def _get_video_info(self) -> dict:
        """Get video metadata"""
        try:
            probe = ffmpeg.probe(str(self.input_path))
            video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            
            return {
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'duration': float(video_stream.get('duration', probe['format']['duration']))
            }
        except Exception as e:
            logger.error(f"Failed to probe video: {e}")
            raise
    
    def cleanup(self):
        """Clean up temporary files"""
        import shutil
        if self.temp_dir.exists():
            try:
                shutil.rmtree(self.temp_dir)
                logger.info("🗑️  Temporary files cleaned up")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp files: {e}")
    
    def _adjust_subtitle_timestamps_after_cuts(self):
        """Adjust subtitle timestamps to match the edited video timeline after jump cuts"""
        # Calculate time offset from cuts
        sorted_cuts = sorted(self.script.timeline.cuts, key=lambda x: x.start)
        
        # For each subtitle, calculate how much time was cut before it
        for segment in self.script.subtitles.segments:
            offset = 0.0
            for cut in sorted_cuts:
                if cut.end <= segment.start:
                    # This cut is entirely before the subtitle
                    offset += (cut.end - cut.start)
                elif cut.start < segment.start < cut.end:
                    # Subtitle starts inside a cut (shouldn't happen, but handle it)
                    offset += (segment.start - cut.start)
                    break
            
            # Apply offset (shift timestamps back by the amount cut)
            segment.start -= offset
            segment.end -= offset
        
        logger.info(f"Adjusted subtitle timestamps (offset calculations complete)")
