# Main Processing Pipeline - AI-Driven Video Editor

import ffmpeg
import logging
from pathlib import Path
from ai_models import AIEditingScript
from processor_audio import AudioProcessor
from processor_video import VideoProcessor
from processor_effects import EffectsProcessor
from processor_subtitles import SubtitleProcessor
from timeline_manager import TimelineManager, adjust_subtitle_timestamps

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
        
        # Initialize Timeline Manager for subtitle sync
        self.timeline = TimelineManager(self.video_info['duration'])
        
        # Initialize processors
        self.audio_processor = AudioProcessor(script.audio, self.temp_dir)
        self.video_processor = VideoProcessor(script.visual, self.temp_dir, self.video_info)
        self.effects_processor = EffectsProcessor(script, self.temp_dir, self.video_info)
        self.subtitle_processor = SubtitleProcessor(script.subtitles, self.temp_dir, self.video_info)
        
        logger.info(f"Pipeline initialized for job: {script.job_id}")
        logger.info(f"Content type: {script.metadata.contentType}, Mood: {script.metadata.mood}")
        logger.info(f"Original video duration: {self.video_info['duration']:.2f}s")
    
    def execute(self) -> Path:
        """Execute full AI-driven processing pipeline"""
        current_video = self.input_path
        
        logger.info("=" * 60)
        logger.info("🎬 Starting AI-Driven Video Processing")
        logger.info("=" * 60)
        
        try:
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
                
                # Register cuts with timeline manager BEFORE applying them
                for cut in self.script.timeline.cuts:
                    try:
                        self.timeline.add_cut(cut.start, cut.end)
                        logger.debug(f"Registered cut: {cut.start:.2f}s - {cut.end:.2f}s ({cut.reason})")
                    except ValueError as e:
                        logger.warning(f"Invalid cut skipped: {e}")
                
                # Log timeline summary
                summary = self.timeline.get_summary()
                logger.info(f"Timeline: {summary['original_duration']:.2f}s → {summary['edited_duration']:.2f}s")
                logger.info(f"Total removed: {summary['total_removed']:.2f}s, Kept segments: {summary['kept_segments']}")
                
                # Apply cuts to video
                current_video = self.video_processor.apply_jump_cuts(
                    current_video,
                    self.script.timeline.cuts
                )
                
                # Adjust subtitle timestamps using TimelineManager
                if self.script.subtitles.segments:
                    logger.info("Adjusting subtitle timestamps after jump cuts...")
                    original_count = len(self.script.subtitles.segments)
                    
                    # Convert subtitle segments to dict format
                    subtitle_dicts = [
                        {
                            'start': seg.start,
                            'end': seg.end,
                            'text': seg.text
                        }
                        for seg in self.script.subtitles.segments
                    ]
                    
                    # Adjust using timeline manager
                    adjusted_dicts = adjust_subtitle_timestamps(subtitle_dicts, self.timeline)
                    
                    # Update script with adjusted subtitles (clamp to valid range)
                    from ai_models import SubtitleSegment
                    self.script.subtitles.segments = [
                        SubtitleSegment(
                            start=max(0.0, sub['start']),  # Clamp to >= 0
                            end=max(0.01, sub['end']),     # Clamp to > 0
                            text=sub['text']
                        )
                        for sub in adjusted_dicts
                        if sub['end'] > 0  # Skip subtitles that are completely cut
                    ]
                    
                    removed_count = original_count - len(self.script.subtitles.segments)
                    logger.info(
                        f"✅ Subtitle timestamps adjusted: {original_count} → {len(self.script.subtitles.segments)} "
                        f"({removed_count} removed from cuts)"
                    )
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
                logger.info(f"Subtitle style: {self.script.subtitles.style.font}, pos: {self.script.subtitles.style.position}")
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
            
            # Log final timeline summary
            if self.script.timeline.cuts:
                final_summary = self.timeline.get_summary()
                logger.info(f"Final Timeline Summary:")
                logger.info(f"  Original: {final_summary['original_duration']:.2f}s")
                logger.info(f"  Edited: {final_summary['edited_duration']:.2f}s")
                logger.info(f"  Removed: {final_summary['total_removed']:.2f}s")
            
            return self.output_path
            
        except Exception as e:
            logger.error(f"❌ Pipeline execution failed: {e}", exc_info=True)
            raise
    
    def _get_video_info(self) -> dict:
        """Get video metadata"""
        try:
            probe = ffmpeg.probe(str(self.input_path))
            video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
            
            info = {
                'width': int(video_stream['width']),
                'height': int(video_stream['height']),
                'duration': float(video_stream.get('duration', probe['format']['duration']))
            }
            
            logger.debug(f"Video info: {info['width']}x{info['height']}, {info['duration']:.2f}s")
            return info
            
        except Exception as e:
            logger.error(f"Failed to probe video: {e}", exc_info=True)
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

