"""
Comprehensive test suite for the tower jumps analyzer module.

Tests cover all major functions including analysis logic, event generation,
state estimation, and pattern detection.
"""

import os
import sys
from datetime import datetime, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

# Add the source directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from towerjumps.analyzer import (
    analyze_time_window,
    analyze_tower_jumps,
    analyze_tower_jumps_stream,
    calculate_confidence,
    count_state_changes,
    detect_tower_jump_pattern,
    estimate_most_likely_state,
    generate_analysis_summary,
)
from towerjumps.config import Config
from towerjumps.events import (
    CompletionEvent,
    DataLoadingEvent,
    ErrorEvent,
    ProcessingEvent,
    WindowCreationEvent,
)
from towerjumps.models import LocationRecord, TimeInterval


@pytest.fixture
def sample_config():
    """Sample configuration for tests."""
    return Config(
        time_window_minutes=15,
        max_speed_mph=80.0,
        max_speed_kmh=128.0,
        min_confidence_threshold=0.5,
        state_consistency_weight=0.4,
        duration_weight=0.3,
        record_count_weight=0.3,
        min_tower_jump_distance_km=5.0,
        min_time_for_movement_minutes=5.0,
    )


@pytest.fixture
def sample_location_records():
    """Sample location records for testing."""
    base_time = datetime(2023, 1, 1, 12, 0, 0)
    return [
        LocationRecord(
            page=1,
            item=1,
            utc_datetime=base_time,
            local_datetime=base_time,
            latitude=40.7128,
            longitude=-74.0060,
            timezone="UTC",
            city="New York",
            county="New York",
            state="NY",
            country="US",
            cell_type="4G",
        ),
        LocationRecord(
            page=1,
            item=2,
            utc_datetime=base_time + timedelta(minutes=5),
            local_datetime=base_time + timedelta(minutes=5),
            latitude=40.7589,
            longitude=-73.9851,
            timezone="UTC",
            city="New York",
            county="New York",
            state="NY",
            country="US",
            cell_type="4G",
        ),
        LocationRecord(
            page=1,
            item=3,
            utc_datetime=base_time + timedelta(minutes=10),
            local_datetime=base_time + timedelta(minutes=10),
            latitude=34.0522,
            longitude=-118.2437,
            timezone="UTC",
            city="Los Angeles",
            county="Los Angeles",
            state="CA",
            country="US",
            cell_type="4G",
        ),
    ]


@pytest.fixture
def sample_location_records_no_location():
    """Sample location records without valid location data."""
    base_time = datetime(2023, 1, 1, 12, 0, 0)
    return [
        LocationRecord(
            page=1,
            item=1,
            utc_datetime=base_time,
            local_datetime=base_time,
            latitude=None,
            longitude=None,
            timezone="UTC",
            city="Unknown",
            county="Unknown",
            state="Unknown",
            country="US",
            cell_type="4G",
        ),
        LocationRecord(
            page=1,
            item=2,
            utc_datetime=base_time + timedelta(minutes=5),
            local_datetime=base_time + timedelta(minutes=5),
            latitude=0.0,
            longitude=0.0,
            timezone="UTC",
            city="Unknown",
            county="Unknown",
            state="Unknown",
            country="US",
            cell_type="4G",
        ),
    ]


@pytest.fixture
def sample_dataframe():
    """Sample DataFrame for window analysis tests."""
    base_time = datetime(2023, 1, 1, 12, 0, 0)
    data = {
        "utc_datetime": [
            base_time,
            base_time + timedelta(minutes=5),
            base_time + timedelta(minutes=10),
        ],
        "latitude": [40.7128, 40.7589, 34.0522],
        "longitude": [-74.0060, -73.9851, -118.2437],
        "state": ["NY", "NY", "CA"],
        "distance_km": [0.0, 5.2, 3950.1],
        "speed_kmh": [0.0, 62.4, 23700.6],
        "is_anomalous": [False, False, True],
    }
    return pd.DataFrame(data)


@pytest.fixture
def sample_intervals():
    """Sample time intervals for summary tests."""
    base_time = datetime(2023, 1, 1, 12, 0, 0)
    return [
        TimeInterval(
            start_time=base_time,
            end_time=base_time + timedelta(minutes=15),
            estimated_state="NY",
            is_tower_jump=False,
            confidence=0.85,
            record_count=10,
            states_observed=["NY"],
            max_distance_km=2.1,
            max_speed_kmh=45.0,
        ),
        TimeInterval(
            start_time=base_time + timedelta(minutes=15),
            end_time=base_time + timedelta(minutes=30),
            estimated_state="CA",
            is_tower_jump=True,
            confidence=0.72,
            record_count=8,
            states_observed=["NY", "CA"],
            max_distance_km=3950.1,
            max_speed_kmh=23700.6,
        ),
        TimeInterval(
            start_time=base_time + timedelta(minutes=30),
            end_time=base_time + timedelta(minutes=45),
            estimated_state="CA",
            is_tower_jump=False,
            confidence=0.91,
            record_count=12,
            states_observed=["CA"],
            max_distance_km=1.8,
            max_speed_kmh=35.2,
        ),
    ]


class TestAnalyzeTowerJumps:
    """Test the main analyze_tower_jumps function."""

    @patch("towerjumps.analyzer.filter_records_with_location")
    @patch("towerjumps.analyzer.records_to_dataframe")
    @patch("towerjumps.analyzer.add_distances_and_speeds")
    @patch("towerjumps.analyzer.add_anomaly_detection")
    @patch("towerjumps.analyzer.create_data_driven_time_windows")
    def test_analyze_tower_jumps_success(
        self,
        mock_windows,
        mock_anomaly,
        mock_distances,
        mock_dataframe,
        mock_filter,
        sample_location_records,
        sample_config,
        sample_dataframe,
    ):
        """Test successful analysis flow."""
        # Setup mocks
        mock_filter.return_value = sample_location_records
        mock_dataframe.return_value = sample_dataframe
        mock_distances.return_value = sample_dataframe
        mock_anomaly.return_value = sample_dataframe

        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_windows.return_value = [
            (base_time, base_time + timedelta(minutes=15)),
            (base_time + timedelta(minutes=15), base_time + timedelta(minutes=30)),
        ]

        # Run analysis
        events = list(analyze_tower_jumps(sample_location_records, sample_config))

        # Extract final result
        completion_events = [e for e in events if isinstance(e, CompletionEvent)]
        if completion_events:
            # intervals variable was assigned but never used, removing it
            pass

        # Verify events were generated
        assert len(events) > 0
        assert any(isinstance(e, DataLoadingEvent) for e in events)
        assert any(isinstance(e, ProcessingEvent) for e in events)
        assert any(isinstance(e, WindowCreationEvent) for e in events)
        assert any(isinstance(e, CompletionEvent) for e in events)

    def test_analyze_tower_jumps_no_location_data(self, sample_location_records_no_location, sample_config):
        """Test analysis with no valid location data."""
        events = list(analyze_tower_jumps(sample_location_records_no_location, sample_config))

        # Should get error event for no location data
        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        assert len(error_events) > 0
        assert "No records with location data found" in error_events[0].message

    def test_analyze_tower_jumps_empty_records(self, sample_config):
        """Test analysis with empty records list."""
        events = list(analyze_tower_jumps([], sample_config))

        # Should get error event for no data
        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        assert len(error_events) > 0

    @patch("towerjumps.analyzer.filter_records_with_location")
    def test_analyze_tower_jumps_exception_handling(self, mock_filter, sample_location_records, sample_config):
        """Test that exceptions are properly handled and reported."""
        # Make filter_records_with_location raise an exception
        mock_filter.side_effect = ValueError("Test exception")

        events = list(analyze_tower_jumps(sample_location_records, sample_config))

        # Should get error event
        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        assert len(error_events) > 0
        assert "Analysis failed" in error_events[0].message


class TestAnalyzeTowerJumpsStream:
    """Test the streaming async version of tower jumps analysis."""

    @pytest.mark.asyncio
    async def test_analyze_tower_jumps_stream_success(self, sample_location_records, sample_config):
        """Test successful streaming async analysis."""

        # Create a generator function that yields events and returns result
        def mock_generator():
            yield DataLoadingEvent("Test event")
            yield CompletionEvent("Test completion", summary={}, total_intervals=1, tower_jumps=0)
            return []  # Return empty list as final result

        with patch("towerjumps.analyzer.analyze_tower_jumps", return_value=mock_generator()):
            # Collect events from the async generator
            events = []
            async for event in analyze_tower_jumps_stream(sample_location_records, sample_config):
                events.append(event)

            # Verify we received events
            assert len(events) >= 2  # At least DataLoadingEvent and CompletionEvent
            assert any(isinstance(e, DataLoadingEvent) for e in events)
            assert any(isinstance(e, CompletionEvent) for e in events)

    @pytest.mark.asyncio
    async def test_analyze_tower_jumps_stream_exception(self, sample_location_records, sample_config):
        """Test streaming async analysis exception handling."""

        with patch("towerjumps.analyzer.analyze_tower_jumps") as mock_analyze:
            mock_analyze.side_effect = ValueError("Test async exception")

            # Collect events from the async generator
            events = []
            async for event in analyze_tower_jumps_stream(sample_location_records, sample_config):
                events.append(event)

            # Should get error event
            error_events = [e for e in events if isinstance(e, ErrorEvent)]
            assert len(error_events) > 0
            assert "Analysis error" in error_events[0].message


class TestAnalyzeTimeWindow:
    """Test the analyze_time_window function."""

    def test_analyze_time_window_success(self, sample_dataframe, sample_config):
        """Test successful time window analysis."""
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = start_time + timedelta(minutes=15)

        interval = analyze_time_window(sample_dataframe, start_time, end_time, sample_config)

        assert isinstance(interval, TimeInterval)
        assert interval.start_time == start_time
        assert interval.end_time == end_time
        assert interval.estimated_state in ["NY", "CA", "Unknown"]
        assert isinstance(interval.is_tower_jump, bool)
        assert 0.0 <= interval.confidence <= 1.0
        assert interval.record_count >= 0

    def test_analyze_time_window_empty_data(self, sample_config):
        """Test time window analysis with empty DataFrame."""
        # Create empty DataFrame with required columns
        empty_df = pd.DataFrame(
            columns=["utc_datetime", "latitude", "longitude", "state", "distance_km", "speed_kmh", "is_anomalous"]
        )
        start_time = datetime(2023, 1, 1, 12, 0, 0)
        end_time = start_time + timedelta(minutes=15)

        interval = analyze_time_window(empty_df, start_time, end_time, sample_config)

        assert interval.estimated_state == "Unknown"
        assert interval.is_tower_jump is False
        assert interval.confidence == 0.0
        assert interval.record_count == 0

    def test_analyze_time_window_no_data_in_window(self, sample_dataframe, sample_config):
        """Test time window analysis when no data falls within the window."""
        # Use a time window that doesn't overlap with sample data
        start_time = datetime(2023, 1, 2, 12, 0, 0)  # Next day
        end_time = start_time + timedelta(minutes=15)

        interval = analyze_time_window(sample_dataframe, start_time, end_time, sample_config)

        assert interval.estimated_state == "Unknown"
        assert interval.is_tower_jump is False
        assert interval.confidence == 0.0
        assert interval.record_count == 0


class TestEstimateMostLikelyState:
    """Test the estimate_most_likely_state function."""

    def test_estimate_most_likely_state_success(self):
        """Test successful state estimation."""
        df = pd.DataFrame({"state": ["NY", "NY", "NY", "CA", "CA"]})

        result = estimate_most_likely_state(df)
        assert result == "NY"  # Most frequent state

    def test_estimate_most_likely_state_empty_df(self):
        """Test state estimation with empty DataFrame."""
        df = pd.DataFrame()
        result = estimate_most_likely_state(df)
        assert result == "Unknown"

    def test_estimate_most_likely_state_no_valid_states(self):
        """Test state estimation when all states are null."""
        df = pd.DataFrame({"state": [None, None, None]})

        result = estimate_most_likely_state(df)
        assert result == "Unknown"

    def test_estimate_most_likely_state_tie(self):
        """Test state estimation when there's a tie."""
        df = pd.DataFrame({"state": ["NY", "CA"]})

        result = estimate_most_likely_state(df)
        assert result in ["NY", "CA"]  # Either is acceptable for a tie


class TestDetectTowerJumpPattern:
    """Test the detect_tower_jump_pattern function."""

    def test_detect_tower_jump_pattern_high_speed(self, sample_config):
        """Test tower jump detection based on high speed."""
        df = pd.DataFrame({
            "state": ["NY", "CA"],
            "speed_kmh": [50.0, 200.0],  # One speed exceeds threshold
            "is_anomalous": [False, False],
        })

        result = detect_tower_jump_pattern(df, sample_config)
        assert result is True

    def test_detect_tower_jump_pattern_anomalous_movement(self, sample_config):
        """Test tower jump detection based on anomalous movement."""
        df = pd.DataFrame({
            "state": ["NY", "CA"],
            "speed_kmh": [50.0, 60.0],  # Normal speeds
            "is_anomalous": [False, True],  # One anomalous movement
        })

        result = detect_tower_jump_pattern(df, sample_config)
        assert result is True

    def test_detect_tower_jump_pattern_rapid_state_changes(self, sample_config):
        """Test tower jump detection based on rapid state changes."""
        df = pd.DataFrame({
            "state": ["NY", "CA", "TX", "FL"],  # Multiple state changes
            "speed_kmh": [50.0, 60.0, 55.0, 58.0],  # Normal speeds
            "is_anomalous": [False, False, False, False],
        })

        result = detect_tower_jump_pattern(df, sample_config)
        assert result is True

    def test_detect_tower_jump_pattern_no_pattern(self, sample_config):
        """Test when no tower jump pattern is detected."""
        df = pd.DataFrame({
            "state": ["NY", "NY", "NY"],  # Same state
            "speed_kmh": [50.0, 55.0, 52.0],  # Normal speeds
            "is_anomalous": [False, False, False],
        })

        result = detect_tower_jump_pattern(df, sample_config)
        assert result is False

    def test_detect_tower_jump_pattern_empty_df(self, sample_config):
        """Test tower jump detection with empty DataFrame."""
        df = pd.DataFrame()
        result = detect_tower_jump_pattern(df, sample_config)
        assert result is False

    def test_detect_tower_jump_pattern_insufficient_data(self, sample_config):
        """Test tower jump detection with insufficient data."""
        df = pd.DataFrame({"state": ["NY"], "speed_kmh": [50.0], "is_anomalous": [False]})

        result = detect_tower_jump_pattern(df, sample_config)
        assert result is False


class TestCountStateChanges:
    """Test the count_state_changes function."""

    def test_count_state_changes_multiple_changes(self):
        """Test counting state changes with multiple changes."""
        df = pd.DataFrame({"state": ["NY", "CA", "CA", "TX", "TX", "FL"]})

        result = count_state_changes(df)
        assert result == 3  # NY->CA, CA->TX, TX->FL

    def test_count_state_changes_no_changes(self):
        """Test counting state changes when all states are the same."""
        df = pd.DataFrame({"state": ["NY", "NY", "NY", "NY"]})

        result = count_state_changes(df)
        assert result == 0

    def test_count_state_changes_empty_df(self):
        """Test counting state changes with empty DataFrame."""
        df = pd.DataFrame()
        result = count_state_changes(df)
        assert result == 0

    def test_count_state_changes_single_record(self):
        """Test counting state changes with single record."""
        df = pd.DataFrame({"state": ["NY"]})

        result = count_state_changes(df)
        assert result == 0

    def test_count_state_changes_with_nulls(self):
        """Test counting state changes when some states are null."""
        df = pd.DataFrame({"state": ["NY", None, "CA", "CA"]})

        result = count_state_changes(df)
        assert result == 1  # Only NY->CA counted (nulls ignored)


class TestCalculateConfidence:
    """Test the calculate_confidence function."""

    def test_calculate_confidence_high_consistency(self, sample_config):
        """Test confidence calculation with high state consistency."""
        df = pd.DataFrame({
            "state": ["NY", "NY", "NY", "NY", "NY"],
            "is_anomalous": [False, False, False, False, False],
        })

        confidence = calculate_confidence(df, "NY", sample_config)
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # Should be high due to consistency

    def test_calculate_confidence_low_consistency(self, sample_config):
        """Test confidence calculation with low state consistency."""
        df = pd.DataFrame({
            "state": ["NY", "CA", "TX", "FL", "WA", "GA", "MI"],
            "is_anomalous": [False, False, False, False, False, False, False],
        })

        confidence = calculate_confidence(df, "NY", sample_config)
        assert 0.0 <= confidence <= 1.0
        assert confidence < 0.6  # Should be low due to inconsistency

    def test_calculate_confidence_with_anomalies(self, sample_config):
        """Test confidence calculation with anomalous data."""
        df = pd.DataFrame({"state": ["NY", "NY", "NY"], "is_anomalous": [True, True, True]})

        confidence = calculate_confidence(df, "NY", sample_config)
        assert 0.0 <= confidence <= 1.0
        # Should be penalized for anomalies

    def test_calculate_confidence_empty_df(self, sample_config):
        """Test confidence calculation with empty DataFrame."""
        df = pd.DataFrame()
        confidence = calculate_confidence(df, "NY", sample_config)
        assert confidence == 0.0

    def test_calculate_confidence_no_state_records(self, sample_config):
        """Test confidence calculation when no valid state records exist."""
        df = pd.DataFrame({"state": [None, None, None], "is_anomalous": [False, False, False]})

        confidence = calculate_confidence(df, "NY", sample_config)
        assert confidence == 0.0


class TestGenerateAnalysisSummary:
    """Test the generate_analysis_summary function."""

    def test_generate_analysis_summary_success(self, sample_intervals):
        """Test successful summary generation."""
        summary = generate_analysis_summary(sample_intervals)

        assert "total_intervals" in summary
        assert "tower_jump_intervals" in summary
        assert "tower_jump_percentage" in summary
        assert "most_common_state" in summary
        assert "average_confidence" in summary
        assert "states_observed" in summary

        assert summary["total_intervals"] == 3
        assert summary["tower_jump_intervals"] == 1
        assert summary["tower_jump_percentage"] == pytest.approx(33.33, rel=0.1)
        assert summary["most_common_state"] in ["NY", "CA"]
        assert 0.0 <= summary["average_confidence"] <= 1.0

    def test_generate_analysis_summary_empty_intervals(self):
        """Test summary generation with empty intervals list."""
        summary = generate_analysis_summary([])
        assert summary == {}

    def test_generate_analysis_summary_no_tower_jumps(self):
        """Test summary generation when no tower jumps are detected."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        intervals = [
            TimeInterval(
                start_time=base_time,
                end_time=base_time + timedelta(minutes=15),
                estimated_state="NY",
                is_tower_jump=False,
                confidence=0.85,
                record_count=10,
                states_observed=["NY"],
            ),
            TimeInterval(
                start_time=base_time + timedelta(minutes=15),
                end_time=base_time + timedelta(minutes=30),
                estimated_state="NY",
                is_tower_jump=False,
                confidence=0.90,
                record_count=12,
                states_observed=["NY"],
            ),
        ]

        summary = generate_analysis_summary(intervals)
        assert summary["tower_jump_intervals"] == 0
        assert summary["tower_jump_percentage"] == 0.0

    def test_generate_analysis_summary_all_unknown_states(self):
        """Test summary generation when all states are unknown."""
        base_time = datetime(2023, 1, 1, 12, 0, 0)
        intervals = [
            TimeInterval(
                start_time=base_time,
                end_time=base_time + timedelta(minutes=15),
                estimated_state="Unknown",
                is_tower_jump=False,
                confidence=0.0,
                record_count=0,
                states_observed=[],
            ),
        ]

        summary = generate_analysis_summary(intervals)
        assert summary["most_common_state"] == "Unknown"


class TestIntegration:
    """Integration tests combining multiple functions."""

    @patch("towerjumps.analyzer.filter_records_with_location")
    @patch("towerjumps.analyzer.records_to_dataframe")
    @patch("towerjumps.analyzer.add_distances_and_speeds")
    @patch("towerjumps.analyzer.add_anomaly_detection")
    @patch("towerjumps.analyzer.create_data_driven_time_windows")
    def test_full_analysis_pipeline(
        self,
        mock_windows,
        mock_anomaly,
        mock_distances,
        mock_dataframe,
        mock_filter,
        sample_location_records,
        sample_config,
        sample_dataframe,
    ):
        """Test the complete analysis pipeline end-to-end."""
        # Setup mocks
        mock_filter.return_value = sample_location_records
        mock_dataframe.return_value = sample_dataframe
        mock_distances.return_value = sample_dataframe
        mock_anomaly.return_value = sample_dataframe

        base_time = datetime(2023, 1, 1, 12, 0, 0)
        mock_windows.return_value = [
            (base_time, base_time + timedelta(minutes=15)),
        ]

        # Run analysis
        events = list(analyze_tower_jumps(sample_location_records, sample_config))

        # Verify we get expected event types
        event_types = [type(e).__name__ for e in events]
        expected_types = ["DataLoadingEvent", "ProcessingEvent", "WindowCreationEvent", "CompletionEvent"]

        for expected_type in expected_types:
            assert any(expected_type in event_type for event_type in event_types), (
                f"Expected {expected_type} in {event_types}"
            )

    def test_state_estimation_integration(self):
        """Test state estimation with realistic data patterns."""
        # Create DataFrame with realistic state distribution
        df = pd.DataFrame({
            "state": ["NY"] * 8 + ["CA"] * 2,  # 80% NY, 20% CA
            "is_anomalous": [False] * 10,  # No anomalous movements
        })

        estimated_state = estimate_most_likely_state(df)
        assert estimated_state == "NY"

        # Test confidence calculation for this state
        config = Config()
        confidence = calculate_confidence(df, estimated_state, config)
        assert confidence > 0.5  # Should be confident about NY

    def test_tower_jump_detection_integration(self):
        """Test tower jump detection with realistic scenarios."""
        config = Config()

        # Scenario 1: Normal movement (no tower jump)
        normal_df = pd.DataFrame({
            "state": ["NY", "NY", "NY"],
            "speed_kmh": [45.0, 50.0, 48.0],
            "is_anomalous": [False, False, False],
        })

        assert detect_tower_jump_pattern(normal_df, config) is False

        # Scenario 2: Rapid cross-country movement (tower jump)
        jump_df = pd.DataFrame({
            "state": ["NY", "CA", "FL"],
            "speed_kmh": [45.0, 250.0, 180.0],  # High speeds
            "is_anomalous": [False, True, True],
        })

        assert detect_tower_jump_pattern(jump_df, config) is True


# Parametrized tests for edge cases
@pytest.mark.parametrize(
    "speed_kmh,expected",
    [
        (50.0, False),  # Normal speed
        (150.0, True),  # High speed
        (0.0, False),  # Zero speed
        (float("inf"), True),  # Infinite speed
    ],
)
def test_speed_threshold_detection(speed_kmh, expected):
    """Test speed threshold detection with various speeds."""
    config = Config(max_speed_kmh=128.0)
    df = pd.DataFrame({"state": ["NY", "CA"], "speed_kmh": [50.0, speed_kmh], "is_anomalous": [False, False]})

    result = detect_tower_jump_pattern(df, config)
    assert result == expected


@pytest.mark.parametrize(
    "states,expected_changes",
    [
        (["NY"], 0),
        (["NY", "NY"], 0),
        (["NY", "CA"], 1),
        (["NY", "CA", "TX"], 2),
        (["NY", "CA", "NY"], 2),
        ([], 0),
    ],
)
def test_state_change_counting(states, expected_changes):
    """Test state change counting with various state sequences."""
    df = pd.DataFrame({"state": states}) if states else pd.DataFrame()

    result = count_state_changes(df)
    assert result == expected_changes
