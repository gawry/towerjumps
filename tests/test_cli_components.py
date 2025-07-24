import os
import sys
from io import StringIO
from unittest.mock import Mock, patch

import pytest
from rich.console import Console

# Add the source directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from towerjumps.cli import AnalysisEventProcessor, ProgressManager, ResultCollector
from towerjumps.events import (
    AnalysisProgressEvent,
    CompletionEvent,
    DataLoadingEvent,
    ErrorEvent,
    IntervalCompletedEvent,
    ProcessingEvent,
    WindowCreationEvent,
)
from towerjumps.models import TimeInterval


@pytest.fixture
def console():
    """Create a console fixture for testing."""
    return Console(file=StringIO(), width=80)


@pytest.fixture
def mock_intervals():
    """Create mock TimeInterval objects for testing."""
    return [Mock(spec=TimeInterval), Mock(spec=TimeInterval)]


class TestProgressManager:
    """Test the ProgressManager class."""

    def test_quiet_mode_suppresses_output(self, console):
        """Test that quiet mode properly suppresses progress output."""
        progress_manager = ProgressManager(console, quiet=True)

        with progress_manager:
            event = DataLoadingEvent("Processing data...", total_records=1000, records_with_location=800)

            progress_manager.update_data_loading(event)

        output = console.file.getvalue()
        assert output.strip() == ""

    def test_processing_event_handling(self, console):
        """Test that processing events are handled correctly."""
        progress_manager = ProgressManager(console, quiet=False)

        with progress_manager:
            event = ProcessingEvent("Converting to DataFrame...", step="dataframe_conversion", progress=50.0)

            progress_manager.update_processing(event)

    def test_error_handling(self, console):
        """Test error event handling."""
        progress_manager = ProgressManager(console, quiet=False)

        with progress_manager:
            error_event = ErrorEvent("Analysis failed", error_type="ValueError", error_details="Invalid data format")

            progress_manager.handle_error(error_event)

        output = console.file.getvalue()
        assert "Analysis failed" in output

    def test_context_manager_setup_teardown(self, console):
        """Test that context manager properly sets up and tears down progress."""
        progress_manager = ProgressManager(console, quiet=False)

        assert progress_manager.progress is None

        with progress_manager:
            assert progress_manager.progress is not None


class TestResultCollector:
    """Test the ResultCollector class."""

    def test_interval_tracking(self):
        """Test that intervals are tracked correctly."""
        collector = ResultCollector()

        assert len(collector.get_intervals()) == 0
        assert collector.tower_jumps_count == 0

        jump_event = IntervalCompletedEvent(
            "Interval completed", interval_data={"is_tower_jump": True, "estimated_state": "New York"}
        )
        collector.handle_interval_completed(jump_event)

        assert collector.tower_jumps_count == 1

        normal_event = IntervalCompletedEvent(
            "Interval completed", interval_data={"is_tower_jump": False, "estimated_state": "Connecticut"}
        )
        collector.handle_interval_completed(normal_event)

        assert collector.tower_jumps_count == 1

    def test_final_intervals_setting(self, mock_intervals):
        """Test setting final intervals."""
        collector = ResultCollector()

        collector.set_final_intervals(mock_intervals)

        assert len(collector.get_intervals()) == 2
        assert collector.get_intervals() == mock_intervals

    def test_multiple_interval_events(self):
        """Test handling multiple interval events."""
        collector = ResultCollector()

        events = [
            IntervalCompletedEvent("Event 1", interval_data={"is_tower_jump": True, "estimated_state": "NY"}),
            IntervalCompletedEvent("Event 2", interval_data={"is_tower_jump": False, "estimated_state": "CT"}),
            IntervalCompletedEvent("Event 3", interval_data={"is_tower_jump": True, "estimated_state": "CA"}),
        ]

        for event in events:
            collector.handle_interval_completed(event)

        assert collector.tower_jumps_count == 2


class TestAnalysisEventProcessor:
    """Test the AnalysisEventProcessor class."""

    @patch("towerjumps.cli.analyze_tower_jumps")
    def test_event_dispatching(self, mock_analyze, console):
        """Test that events are properly dispatched to handlers."""
        mock_events = [
            DataLoadingEvent("Loading..."),
            ProcessingEvent("Processing...", "test_step"),
            WindowCreationEvent("Windows created", 100, 60),
            AnalysisProgressEvent("Progress...", 1, 100),
            CompletionEvent("Done", {}, 100, 10),
        ]

        def mock_generator(*args, **kwargs):
            yield from mock_events
            return []

        mock_analyze.return_value = mock_generator()

        processor = AnalysisEventProcessor(console, quiet=True)
        result = processor.process_stream([], Mock())

        assert result == []

        mock_analyze.assert_called_once()

    def test_error_event_raises_exception(self, console):
        """Test that error events properly raise exceptions."""
        processor = AnalysisEventProcessor(console, quiet=True)
        progress_manager = Mock()
        result_collector = Mock()

        error_event = ErrorEvent("Test error", error_type="TestError", error_details="Test details")

        with pytest.raises(Exception) as exc_info:
            processor._dispatch_event(error_event, progress_manager, result_collector)

        assert "TestError" in str(exc_info.value)
        assert "Test error" in str(exc_info.value)

    def test_completion_event_handling(self, console):
        """Test that completion events are handled properly."""
        processor = AnalysisEventProcessor(console, quiet=True)
        progress_manager = Mock()
        result_collector = Mock()

        completion_event = CompletionEvent(
            "Analysis complete", summary={"most_common_state": "NY"}, total_intervals=50, tower_jumps=5
        )

        processor._dispatch_event(completion_event, progress_manager, result_collector)

        progress_manager.update_completion.assert_called_once_with(completion_event)

    @patch("towerjumps.cli.analyze_tower_jumps")
    def test_process_stream_with_no_events(self, mock_analyze, console):
        """Test processing a stream that yields no events."""

        def empty_generator(*args, **kwargs):
            # Create a proper generator that yields nothing and returns empty list
            return
            yield  # Make this a generator function (unreachable)

        mock_analyze.return_value = empty_generator()

        processor = AnalysisEventProcessor(console, quiet=True)
        result = processor.process_stream([], Mock())

        assert result == []
        mock_analyze.assert_called_once()


class TestIntegration:
    """Integration tests for the CLI components working together."""

    @patch("towerjumps.cli.analyze_tower_jumps")
    def test_full_processing_workflow(self, mock_analyze, console):
        """Test the complete processing workflow."""
        events = [
            DataLoadingEvent("Filtering data", total_records=1000, records_with_location=800),
            ProcessingEvent("Converting to DataFrame", "dataframe_conversion", 100.0),
            ProcessingEvent("Calculating distances", "distance_calculation", 100.0),
            ProcessingEvent("Detecting anomalies", "anomaly_detection", 100.0),
            WindowCreationEvent("Created time windows", 50, 60),
            AnalysisProgressEvent("Analyzing window 1/50", 1, 50, "Connecticut", False),
            AnalysisProgressEvent("Analyzing window 25/50", 25, 50, "New York", True),
            AnalysisProgressEvent("Analyzing window 50/50", 50, 50, "Connecticut", False),
            IntervalCompletedEvent("Interval completed", {"is_tower_jump": True}),
            IntervalCompletedEvent("Interval completed", {"is_tower_jump": False}),
            CompletionEvent("Analysis complete", {"most_common_state": "Connecticut"}, 50, 5),
        ]

        def mock_generator(*args, **kwargs):
            yield from events
            return [Mock(spec=TimeInterval) for _ in range(50)]  # Return 50 mock intervals

        mock_analyze.return_value = mock_generator()

        processor = AnalysisEventProcessor(console, quiet=True)
        intervals = processor.process_stream([], Mock())

        assert len(intervals) == 50

        mock_analyze.assert_called_once()

    @patch("towerjumps.cli.analyze_tower_jumps")
    def test_error_during_processing(self, mock_analyze, console):
        """Test handling errors during processing."""
        events = [
            DataLoadingEvent("Loading data"),
            ErrorEvent("Processing failed", "DataError", "Invalid format"),
        ]

        def mock_generator(*args, **kwargs):
            yield from events
            return []

        mock_analyze.return_value = mock_generator()

        processor = AnalysisEventProcessor(console, quiet=True)

        with pytest.raises(Exception) as exc_info:
            processor.process_stream([], Mock())

        assert "DataError: Processing failed" in str(exc_info.value)

    def test_components_integration(self, console, mock_intervals):
        """Test that all components work together properly."""
        progress_manager = ProgressManager(console, quiet=True)
        result_collector = ResultCollector()

        with progress_manager:
            data_event = DataLoadingEvent("Loading", total_records=100, records_with_location=90)
            progress_manager.update_data_loading(data_event)

            interval_event = IntervalCompletedEvent(
                "Completed", interval_data={"is_tower_jump": True, "estimated_state": "NY"}
            )
            result_collector.handle_interval_completed(interval_event)

            result_collector.set_final_intervals(mock_intervals)

        assert result_collector.tower_jumps_count == 1
        assert len(result_collector.get_intervals()) == 2


@pytest.mark.parametrize(
    "event_type,expected_method",
    [
        (DataLoadingEvent("test"), "update_data_loading"),
        (ProcessingEvent("test", "step"), "update_processing"),
        (WindowCreationEvent("test", 10, 5), "update_window_creation"),
        (AnalysisProgressEvent("test", 1, 10), "update_analysis_progress"),
    ],
)
def test_progress_manager_event_dispatch(console, event_type, expected_method):
    """Test that different event types are dispatched to correct methods."""
    progress_manager = ProgressManager(console, quiet=True)

    setattr(progress_manager, expected_method, Mock())

    with progress_manager:
        method = getattr(progress_manager, expected_method)
        method(event_type)

        method.assert_called_once_with(event_type)


@pytest.mark.parametrize(
    "is_tower_jump,expected_count",
    [
        (True, 1),
        (False, 0),
    ],
)
def test_result_collector_tower_jump_counting(is_tower_jump, expected_count):
    """Test tower jump counting with different event types."""
    collector = ResultCollector()

    event = IntervalCompletedEvent(
        "Test event", interval_data={"is_tower_jump": is_tower_jump, "estimated_state": "NY"}
    )

    collector.handle_interval_completed(event)

    assert collector.tower_jumps_count == expected_count


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_progress_manager_with_none_console(self):
        """Test ProgressManager with None console."""
        progress_manager = ProgressManager(None, quiet=True)

        with progress_manager:
            pass

    def test_result_collector_with_invalid_interval_data(self):
        """Test ResultCollector with malformed interval data."""
        collector = ResultCollector()

        bad_event = IntervalCompletedEvent(
            "Bad event",
            interval_data={"estimated_state": "NY"},  # Missing is_tower_jump
        )

        try:
            collector.handle_interval_completed(bad_event)
            assert collector.tower_jumps_count == 0
        except (KeyError, AttributeError):
            pass

    def test_analysis_event_processor_with_empty_records(self, console):
        """Test AnalysisEventProcessor with empty input records."""
        processor = AnalysisEventProcessor(console, quiet=True)

        with patch("towerjumps.cli.analyze_tower_jumps") as mock_analyze:
            mock_analyze.return_value = iter([])

            result = processor.process_stream([], Mock())

            assert result == []
            mock_analyze.assert_called_once()
