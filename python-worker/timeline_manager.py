# Timeline Manager - Handle timeline transformations after jump cuts
# Fixes the subtitle synchronization bug

from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class TimeInterval:
    """Represents a time interval"""
    start: float
    end: float
    
    def __post_init__(self):
        if self.start > self.end:
            raise ValueError(f"Invalid interval: start ({self.start}) > end ({self.end})")
    
    @property
    def duration(self) -> float:
        return self.end - self.start
    
    def contains(self, timestamp: float) -> bool:
        """Check if timestamp is within this interval"""
        return self.start <= timestamp <= self.end
    
    def overlaps(self, other: 'TimeInterval') -> bool:
        """Check if this interval overlaps with another"""
        return self.start < other.end and other.start < self.end


class TimelineManager:
    """
    Manages timeline transformations for video editing
    
    Handles:
    - Removing segments (jump cuts)
    - Mapping timestamps from original to edited timeline
    - Handling edge cases (overlapping cuts, nested cuts, etc.)
    """
    
    def __init__(self, original_duration: float):
        """
        Initialize timeline manager
        
        Args:
            original_duration: Total duration of original video in seconds
        """
        if original_duration <= 0:
            raise ValueError("Duration must be positive")
        
        self.original_duration = original_duration
        self.removed_intervals: List[TimeInterval] = []
        self._sorted = True
    
    def add_cut(self, start: float, end: float) -> None:
        """
        Remove a segment from the timeline
        
        Args:
            start: Cut start time in seconds
            end: Cut end time in seconds
        
        Raises:
            ValueError: If cut is invalid
        """
        # Validate cut
        if start < 0 or end > self.original_duration:
            raise ValueError(
                f"Cut ({start}, {end}) out of bounds (0, {self.original_duration})"
            )
        
        if start >= end:
            raise ValueError(f"Invalid cut: start ({start}) >= end ({end})")
        
        # Add to removed intervals
        self.removed_intervals.append(TimeInterval(start, end))
        self._sorted = False
    
    def _ensure_sorted(self):
        """Ensure removed intervals are sorted by start time"""
        if not self._sorted:
            self.removed_intervals.sort(key=lambda x: x.start)
            self._sorted = True
    
    def _merge_overlapping_cuts(self) -> List[TimeInterval]:
        """
        Merge overlapping cuts into continuous segments
        
        Returns:
            List of non-overlapping merged intervals
        """
        if not self.removed_intervals:
            return []
        
        self._ensure_sorted()
        
        merged: List[TimeInterval] = []
        current = self.removed_intervals[0]
        
        for interval in self.removed_intervals[1:]:
            if current.overlaps(interval) or current.end == interval.start:
                # Merge overlapping/adjacent intervals
                current = TimeInterval(
                    current.start,
                    max(current.end, interval.end)
                )
            else:
                merged.append(current)
                current = interval
        
        merged.append(current)
        return merged
    
    def map_timestamp(self, original_timestamp: float) -> float:
        """
        Map timestamp from original timeline to edited timeline
        
        Args:
            original_timestamp: Timestamp in original video
            
        Returns:
            Timestamp in edited video after cuts applied
        """
        if original_timestamp < 0:
            return 0
        
        if original_timestamp > self.original_duration:
            return self.get_edited_duration()
        
        # Merge overlapping cuts first
        merged_cuts = self._merge_overlapping_cuts()
        
        # Calculate total time removed before this timestamp
        removed_before = 0.0
        
        for cut in merged_cuts:
            if cut.end <= original_timestamp:
                # This cut is entirely before the timestamp
                removed_before += cut.duration
            elif cut.start < original_timestamp < cut.end:
                # Timestamp falls inside a cut
                # Map it to the cut start point (after adjustment)
                removed_before += (original_timestamp - cut.start)
                return cut.start - removed_before
            else:
                # Cut is after timestamp, stop counting
                break
        
        return original_timestamp - removed_before
    
    def get_edited_duration(self) -> float:
        """
        Get total duration of edited video
        
        Returns:
            Duration after all cuts applied
        """
        merged_cuts = self._merge_overlapping_cuts()
        total_removed = sum(cut.duration for cut in merged_cuts)
        return self.original_duration - total_removed
    
    def get_kept_segments(self) -> List[Tuple[float, float]]:
        """
        Get list of time segments that are kept (not cut)
        
        Returns:
            List of (start, end) tuples for kept segments
        """
        merged_cuts = self._merge_overlapping_cuts()
        
        if not merged_cuts:
            return [(0, self.original_duration)]
        
        segments = []
        current_time = 0.0
        
        for cut in merged_cuts:
            if current_time < cut.start:
                segments.append((current_time, cut.start))
            current_time = cut.end
        
        # Add final segment if there's time after last cut
        if current_time < self.original_duration:
            segments.append((current_time, self.original_duration))
        
        return segments
    
    def validate_timestamp(self, timestamp: float) -> bool:
        """
        Check if timestamp falls in a kept segment
        
        Args:
            timestamp: Timestamp to validate
            
        Returns:
            True if timestamp is in kept segment, False if it's cut
        """
        merged_cuts = self._merge_overlapping_cuts()
        
        for cut in merged_cuts:
            if cut.contains(timestamp):
                return False
        
        return 0 <= timestamp <= self.original_duration
    
    def get_summary(self) -> dict:
        """Get summary of timeline transformations"""
        merged_cuts = self._merge_overlapping_cuts()
        
        return {
            'original_duration': self.original_duration,
            'edited_duration': self.get_edited_duration(),
            'total_cuts': len(self.removed_intervals),
            'merged_cuts': len(merged_cuts),
            'total_removed': sum(cut.duration for cut in merged_cuts),
            'kept_segments': len(self.get_kept_segments()),
        }


def adjust_subtitle_timestamps(
    subtitles: List[dict],
    timeline: TimelineManager
) -> List[dict]:
    """
    Adjust subtitle timestamps based on timeline transformations
    
    Args:
        subtitles: List of subtitle dicts with 'start' and 'end' keys
        timeline: TimelineManager with cuts applied
    
    Returns:
        List of adjusted subtitles (only those not completely cut)
    """
    adjusted = []
    
    for subtitle in subtitles:
        start = subtitle['start']
        end = subtitle['end']
        
        # Check if subtitle is completely within a cut
        if not timeline.validate_timestamp(start) and not timeline.validate_timestamp(end):
            # Both start and end are cut, skip this subtitle
            continue
        
        # Map timestamps to new timeline
        new_start = timeline.map_timestamp(start)
        new_end = timeline.map_timestamp(end)
        
        # Ensure we have valid duration
        if new_end > new_start:
            adjusted_subtitle = subtitle.copy()
            adjusted_subtitle['start'] = new_start
            adjusted_subtitle['end'] = new_end
            adjusted.append(adjusted_subtitle)
    
    return adjusted
