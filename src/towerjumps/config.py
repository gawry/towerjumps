from dataclasses import dataclass


@dataclass
class Config:
    time_window_minutes: int = 15
    max_speed_mph: float = 80.0
    max_speed_kmh: float = 128.0  # ~80 mph

    min_confidence_threshold: float = 0.5
    state_consistency_weight: float = 0.4
    duration_weight: float = 0.3
    record_count_weight: float = 0.3

    min_tower_jump_distance_km: float = 5.0

    min_time_for_movement_minutes: float = 5.0
