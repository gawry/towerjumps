from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union


class EventType(str, Enum):
    DATA_LOADING = "data_loading"
    DATA_VALIDATION = "data_validation"
    FILTERING = "filtering"
    PROCESSING = "processing"
    WINDOW_CREATION = "window_creation"
    ANALYSIS_PROGRESS = "analysis_progress"
    INTERVAL_COMPLETED = "interval_completed"
    COMPLETION = "completion"
    ERROR = "error"


@dataclass
class AnalysisEvent:
    type: EventType
    timestamp: datetime
    message: str
    data: Optional[dict[str, Any]] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "data": self.data or {},
        }


@dataclass
class DataLoadingEvent(AnalysisEvent):
    def __init__(self, message: str, total_records: Optional[int] = None, records_with_location: Optional[int] = None):
        super().__init__(
            type=EventType.DATA_LOADING,
            timestamp=datetime.now(),
            message=message,
            data={"total_records": total_records, "records_with_location": records_with_location}
            if total_records is not None
            else None,
        )


@dataclass
class ValidationEvent(AnalysisEvent):
    def __init__(self, message: str, stats: Optional[dict] = None):
        super().__init__(type=EventType.DATA_VALIDATION, timestamp=datetime.now(), message=message, data=stats)


@dataclass
class ProcessingEvent(AnalysisEvent):
    def __init__(self, message: str, step: str, progress: Optional[float] = None):
        super().__init__(
            type=EventType.PROCESSING,
            timestamp=datetime.now(),
            message=message,
            data={"step": step, "progress": progress},
        )


@dataclass
class WindowCreationEvent(AnalysisEvent):
    def __init__(self, message: str, window_count: int, window_size_minutes: int):
        super().__init__(
            type=EventType.WINDOW_CREATION,
            timestamp=datetime.now(),
            message=message,
            data={"window_count": window_count, "window_size_minutes": window_size_minutes},
        )


@dataclass
class AnalysisProgressEvent(AnalysisEvent):
    def __init__(
        self,
        message: str,
        current_window: int,
        total_windows: int,
        estimated_state: Optional[str] = None,
        is_tower_jump: Optional[bool] = None,
    ):
        progress_pct = (current_window / total_windows * 100) if total_windows > 0 else 0
        super().__init__(
            type=EventType.ANALYSIS_PROGRESS,
            timestamp=datetime.now(),
            message=message,
            data={
                "current_window": current_window,
                "total_windows": total_windows,
                "progress_percentage": round(progress_pct, 1),
                "estimated_state": estimated_state,
                "is_tower_jump": is_tower_jump,
            },
        )


@dataclass
class IntervalCompletedEvent(AnalysisEvent):
    def __init__(self, message: str, interval_data: dict):
        super().__init__(
            type=EventType.INTERVAL_COMPLETED, timestamp=datetime.now(), message=message, data=interval_data
        )


@dataclass
class CompletionEvent(AnalysisEvent):
    def __init__(self, message: str, summary: dict, total_intervals: int, tower_jumps: int):
        super().__init__(
            type=EventType.COMPLETION,
            timestamp=datetime.now(),
            message=message,
            data={
                "summary": summary,
                "total_intervals": total_intervals,
                "tower_jumps_detected": tower_jumps,
                "tower_jump_percentage": (tower_jumps / total_intervals * 100) if total_intervals > 0 else 0,
            },
        )


@dataclass
class ErrorEvent(AnalysisEvent):
    def __init__(self, message: str, error_type: str, error_details: Optional[str] = None):
        super().__init__(
            type=EventType.ERROR,
            timestamp=datetime.now(),
            message=message,
            data={"error_type": error_type, "error_details": error_details},
        )


AnalysisEventType = Union[
    DataLoadingEvent,
    ValidationEvent,
    ProcessingEvent,
    WindowCreationEvent,
    AnalysisProgressEvent,
    IntervalCompletedEvent,
    CompletionEvent,
    ErrorEvent,
]
