from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class LocationRecord:
    """Represents a single location record from carrier data."""

    page: int
    item: int
    utc_datetime: datetime
    local_datetime: datetime
    latitude: Optional[float]
    longitude: Optional[float]
    timezone: Optional[str]
    city: Optional[str]
    county: Optional[str]
    state: Optional[str]
    country: Optional[str]
    cell_type: str

    @property
    def has_location(self) -> bool:
        """Check if this record has valid location data."""
        return self.latitude is not None and self.longitude is not None and self.latitude != 0 and self.longitude != 0


@dataclass
class TimeInterval:
    """Represents an analyzed time interval with location estimation."""

    start_time: datetime
    end_time: datetime
    estimated_state: str
    is_tower_jump: bool
    confidence: float
    record_count: int
    states_observed: list[str]
    max_distance_km: Optional[float] = None
    max_speed_kmh: Optional[float] = None

    def to_csv_row(self) -> dict[str, str]:
        """Convert to CSV row format."""
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "estimated_state": self.estimated_state,
            "is_tower_jump": "yes" if self.is_tower_jump else "no",
            "confidence_percentage": f"{self.confidence * 100:.1f}%",
            "record_count": str(self.record_count),
            "states_observed": "|".join(self.states_observed),
            "max_distance_km": f"{self.max_distance_km:.2f}" if self.max_distance_km else "",
            "max_speed_kmh": f"{self.max_speed_kmh:.2f}" if self.max_speed_kmh else "",
        }
