"""
Comprehensive tests for TimelineManager
Tests all edge cases for subtitle synchronization
"""

import sys
from pathlib import Path

# Add parent directory to path to import timeline_manager
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from timeline_manager import TimelineManager, TimeInterval, adjust_subtitle_timestamps


class TestTimeInterval:
    """Test TimeInterval class"""
    
    def test_valid_interval(self):
        interval = TimeInterval(start=1.0, end=5.0)
        assert interval.duration == 4.0
    
    def test_invalid_interval(self):
        with pytest.raises(ValueError):
            TimeInterval(start=5.0, end=1.0)
    
    def test_contains(self):
        interval = TimeInterval(start=1.0, end=5.0)
        assert interval.contains(3.0)
        assert interval.contains(1.0)
        assert interval.contains(5.0)
        assert not interval.contains(0.5)
        assert not interval.contains(6.0)
    
    def test_overlaps(self):
        i1 = TimeInterval(1.0, 5.0)
        i2 = TimeInterval(3.0, 7.0)  # Overlaps
        i3 = TimeInterval(6.0, 10.0)  # No overlap
        
        assert i1.overlaps(i2)
        assert i2.overlaps(i1)
        assert not i1.overlaps(i3)


class TestTimelineManager:
    """Test TimelineManager class"""
    
    def test_initialization(self):
        timeline = TimelineManager(60.0)
        assert timeline.original_duration == 60.0
        assert timeline.get_edited_duration() == 60.0
    
    def test_invalid_duration(self):
        with pytest.raises(ValueError):
            TimelineManager(-1.0)
    
    def test_single_cut(self):
        """Test single cut removal"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(10.0, 15.0)  # Remove 5 seconds
        
        # Before cut: unchanged
        assert timeline.map_timestamp(5.0) == 5.0
        
        # After cut: shifted left by 5 seconds
        assert timeline.map_timestamp(20.0) == 15.0
        assert timeline.map_timestamp(30.0) == 25.0
        
        # Edited duration should be 55 seconds
        assert timeline.get_edited_duration() == 55.0
    
    def test_multiple_cuts(self):
        """Test multiple non-overlapping cuts"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(5.0, 8.0)   # Remove 3 seconds
        timeline.add_cut(15.0, 20.0)  # Remove 5 seconds
        
        # Before first cut
        assert timeline.map_timestamp(3.0) == 3.0
        
        # Between cuts
        assert timeline.map_timestamp(10.0) == 7.0  # 10 - 3
        
        # After both cuts
        assert timeline.map_timestamp(25.0) == 17.0  # 25 - 3 - 5
        
        # Edited duration
        assert timeline.get_edited_duration() == 52.0  # 60 - 3 - 5
    
    def test_overlapping_cuts(self):
        """Test overlapping cuts are merged"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(10.0, 20.0)
        timeline.add_cut(15.0, 25.0)  # Overlaps with previous
        
        # Should merge into single cut from 10 to 25 (15 seconds)
        assert timeline.get_edited_duration() == 45.0
        
        # Timestamp after merged cut
        assert timeline.map_timestamp(30.0) == 15.0
    
    def test_adjacent_cuts(self):
        """Test adjacent cuts are merged"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(10.0, 20.0)
        timeline.add_cut(20.0, 30.0)  # Adjacent
        
        # Should merge into single cut from 10 to 30
        assert timeline.get_edited_duration() == 40.0
        assert timeline.map_timestamp(35.0) == 15.0
    
    def test_timestamp_inside_cut(self):
        """Test timestamp that falls inside a cut"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(10.0, 20.0)
        
        # Timestamp at 15 (inside cut) should map to cut start
        assert timeline.map_timestamp(15.0) == 10.0
    
    def test_boundary_timestamps(self):
        """Test timestamps at boundaries"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(10.0, 20.0)
        
        # Timestamp at cut start
        assert timeline.map_timestamp(10.0) == 10.0
        
        # Timestamp at cut end
        assert timeline.map_timestamp(20.0) == 10.0
    
    def test_out_of_bounds_timestamps(self):
        """Test timestamps outside video duration"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(10.0, 15.0)
        
        # Negative timestamp
        assert timeline.map_timestamp(-5.0) == 0.0
        
        # Beyond duration
        assert timeline.map_timestamp(100.0) == 55.0  # Edited duration
    
    def test_kept_segments(self):
        """Test getting kept segments"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(10.0, 15.0)
        timeline.add_cut(30.0, 40.0)
        
        segments = timeline.get_kept_segments()
        expected = [
            (0.0, 10.0),
            (15.0, 30.0),
            (40.0, 60.0)
        ]
        assert segments == expected
    
    def test_validate_timestamp(self):
        """Test timestamp validation"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(10.0, 20.0)
        
        # Valid timestamps (not cut)
        assert timeline.validate_timestamp(5.0) is True
        assert timeline.validate_timestamp(25.0) is True
        
        # Invalid timestamps (cut)
        assert timeline.validate_timestamp(15.0) is False
        
        # Out of bounds
        assert timeline.validate_timestamp(-1.0) is False
        assert timeline.validate_timestamp(100.0) is False
    
    def test_summary(self):
        """Test summary generation"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(10.0, 15.0)
        timeline.add_cut(14.0, 20.0)  # Overlapping
        timeline.add_cut(30.0, 40.0)
        
        summary = timeline.get_summary()
        
        assert summary['original_duration'] == 60.0
        assert summary['edited_duration'] == 40.0  # 60 - (10-20) - (30-40)
        assert summary['total_cuts'] == 3
        assert summary['merged_cuts'] == 2  # First two overlapping merged
        assert summary['kept_segments'] == 3


class TestSubtitleAdjustment:
    """Test subtitle timestamp adjustment"""
    
    def test_simple_adjustment(self):
        """Test basic subtitle adjustment"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(10.0, 15.0)
        
        subtitles = [
            {'start': 5.0, 'end': 8.0, 'text': 'Before cut'},
            {'start': 20.0, 'end': 25.0, 'text': 'After cut'},
        ]
        
        adjusted = adjust_subtitle_timestamps(subtitles, timeline)
        
        # First subtitle unchanged
        assert adjusted[0]['start'] == 5.0
        assert adjusted[0]['end'] == 8.0
        
        # Second subtitle shifted left by 5 seconds
        assert adjusted[1]['start'] == 15.0
        assert adjusted[1]['end'] == 20.0
    
    def test_subtitle_inside_cut(self):
        """Test subtitle completely inside a cut is removed"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(10.0, 20.0)
        
        subtitles = [
            {'start': 12.0, 'end': 15.0, 'text': 'Inside cut'},
            {'start': 25.0, 'end': 30.0, 'text': 'After cut'},
        ]
        
        adjusted = adjust_subtitle_timestamps(subtitles, timeline)
        
        # First subtitle should be removed
        # Only second subtitle remains
        assert len(adjusted) == 1
        assert adjusted[0]['text'] == 'After cut'
        assert adjusted[0]['start'] == 15.0  # 25 - 10
    
    def test_subtitle_spanning_cut(self):
        """Test subtitle that spans across a cut"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(15.0, 20.0)
        
        subtitles = [
            {'start': 12.0, 'end': 18.0, 'text': 'Spans cut'},
        ]
        
        adjusted = adjust_subtitle_timestamps(subtitles, timeline)
        
        # Subtitle should be adjusted
        # Start: 12 (unchanged)
        # End: should be mapped
        assert len(adjusted) == 1
        assert adjusted[0]['start'] == 12.0
        # End at 18 is inside cut, maps to cut start
        assert adjusted[0]['end'] == 15.0
    
    def test_multiple_cuts_multiple_subtitles(self):
        """Test complex scenario with multiple cuts and subtitles"""
        timeline = TimelineManager(100.0)
        timeline.add_cut(10.0, 15.0)  # 5s
        timeline.add_cut(30.0, 40.0)  # 10s
        timeline.add_cut(60.0, 70.0)  # 10s
        
        subtitles = [
            {'start': 5.0, 'end': 8.0, 'text': 'Sub 1'},      # Before all cuts
            {'start': 12.0, 'end': 14.0, 'text': 'Sub 2'},    # Inside first cut - removed
            {'start': 20.0, 'end': 25.0, 'text': 'Sub 3'},    # Between first and second cut
            {'start': 35.0, 'end': 38.0, 'text': 'Sub 4'},    # Inside second cut - removed
            {'start': 50.0, 'end': 55.0, 'text': 'Sub 5'},    # Between second and third cut
            {'start': 80.0, 'end': 85.0, 'text': 'Sub 6'},    # After all cuts
        ]
        
        adjusted = adjust_subtitle_timestamps(subtitles, timeline)
        
        # Should have 4 subtitles (removed 2 inside cuts)
        assert len(adjusted) == 4
        
        # Sub 1: unchanged
        assert adjusted[0]['start'] == 5.0
        assert adjusted[0]['end'] == 8.0
        
        # Sub 3: shifted left  by first cut (5s)
        assert adjusted[1]['start'] == 15.0  # 20 - 5
        assert adjusted[1]['end'] == 20.0    # 25 - 5
        
        # Sub 5: shifted by first + second cuts (15s)
        assert adjusted[2]['start'] == 35.0  # 50 - 15
        assert adjusted[2]['end'] == 40.0    # 55 - 15
        
        # Sub 6: shifted by all cuts (25s)
        assert adjusted[3]['start'] == 55.0  # 80 - 25
        assert adjusted[3]['end'] == 60.0    # 85 - 25


class TestEdgeCases:
    """Test edge cases and error conditions"""
    
    def test_no_cuts(self):
        """Test timeline with no cuts"""
        timeline = TimelineManager(60.0)
        
        assert timeline.get_edited_duration() == 60.0
        assert timeline.map_timestamp(30.0) == 30.0
        assert timeline.get_kept_segments() == [(0.0, 60.0)]
    
    def test_entire_video_cut(self):
        """Test cutting entire video"""
        timeline = TimelineManager(60.0)
        timeline.add_cut(0.0, 60.0)
        
        assert timeline.get_edited_duration() == 0.0
        assert timeline.get_kept_segments() == []
    
    def test_invalid_cut_bounds(self):
        """Test cuts with invalid bounds"""
        timeline = TimelineManager(60.0)
        
        with pytest.raises(ValueError):
            timeline.add_cut(-5.0, 10.0)  # Negative start
        
        with pytest.raises(ValueError):
            timeline.add_cut(50.0, 70.0)  # Beyond duration
    
    def test_zero_duration_cut(self):
        """Test cut with zero duration"""
        timeline = TimelineManager(60.0)
        
        with pytest.raises(ValueError):
            timeline.add_cut(10.0, 10.0)  # Zero duration


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
