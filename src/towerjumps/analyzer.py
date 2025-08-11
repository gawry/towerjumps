import asyncio
from collections import Counter
from collections.abc import Generator
from datetime import datetime

import pandas as pd
import structlog
from asgiref.sync import sync_to_async

from towerjumps.config import Config
from towerjumps.events import (
    AnalysisEventType,
    AnalysisProgressEvent,
    CompletionEvent,
    DataLoadingEvent,
    ErrorEvent,
    IntervalCompletedEvent,
    ProcessingEvent,
    WindowCreationEvent,
)
from towerjumps.models import TimeInterval
from towerjumps.utils import (
    add_anomaly_detection,
    add_distances_and_speeds,
    create_time_windows,
    filter_dataframe_with_location,
)

logger = structlog.get_logger(__name__)


# Internal sentinel and helper to safely advance a generator in a worker thread
_STREAM_SENTINEL = object()


def _next_with_stop(iterable):
    """Advance iterator one step. On completion, return (sentinel, final_value) instead of raising StopIteration."""
    try:
        return next(iterable)
    except StopIteration as e:
        # Preserve the generator's return value for logging/metrics
        return (_STREAM_SENTINEL, getattr(e, "value", None))


def analyze_tower_jumps(df: pd.DataFrame, config: Config) -> Generator[AnalysisEventType, None, list[TimeInterval]]:
    logger.info(
        "Starting tower jumps analysis",
        total_records=len(df),
        time_window_minutes=config.time_window_minutes,
        max_speed_mph=config.max_speed_mph,
        confidence_threshold=config.min_confidence_threshold,
    )

    intervals = []

    try:
        logger.debug("Step 1: Starting data filtering", total_records=len(df))
        yield DataLoadingEvent("Starting data filtering...")

        location_df = filter_dataframe_with_location(df)

        if location_df.empty:
            logger.error("No records with location data found", total_records=len(df), records_with_location=0)
            yield ErrorEvent(
                "No records with location data found",
                "DATA_ERROR",
                "All records are missing latitude/longitude coordinates",
            )
            return []

        logger.info(
            "Data filtering completed",
            total_records=len(df),
            records_with_location=len(location_df),
            filter_efficiency=f"{(len(location_df) / len(df) * 100):.1f}%",
        )

        yield DataLoadingEvent(
            "Data filtering completed", total_records=len(df), records_with_location=len(location_df)
        )

        logger.debug("Step 2: Calculating distances and speeds", record_count=len(location_df))
        yield ProcessingEvent("Calculating distances and speeds...", "distance_calculation")

        df_with_metrics = add_distances_and_speeds(location_df)

        logger.debug(
            "Distance and speed calculation completed",
            avg_distance_km=df_with_metrics["distance_km"].mean() if "distance_km" in df_with_metrics else 0,
            max_speed_kmh=df_with_metrics["speed_kmh"].max() if "speed_kmh" in df_with_metrics else 0,
        )
        yield ProcessingEvent("Distance and speed calculation completed", "distance_calculation", 100.0)

        logger.debug(
            "Step 3: Detecting movement anomalies",
            max_speed_threshold_kmh=config.max_speed_kmh,
            min_distance_threshold_km=config.min_tower_jump_distance_km,
        )
        yield ProcessingEvent("Detecting movement anomalies...", "anomaly_detection")

        df_final = add_anomaly_detection(df_with_metrics, config.max_speed_kmh, config.min_tower_jump_distance_km)

        anomaly_count = df_final["is_anomalous"].sum() if "is_anomalous" in df_final else 0
        logger.info(
            "Anomaly detection completed",
            total_records=len(df_final),
            anomalies_detected=anomaly_count,
            anomaly_rate=f"{(anomaly_count / len(df_final) * 100):.1f}%" if len(df_final) > 0 else "0%",
        )
        yield ProcessingEvent("Anomaly detection completed", "anomaly_detection", 100.0)

        logger.debug(
            "Step 4: Creating time windows",
            window_size_minutes=config.time_window_minutes,
            data_timespan_hours=round(
                (df_final["utc_datetime"].max() - df_final["utc_datetime"].min()).total_seconds() / 3600, 1
            ),
        )
        yield ProcessingEvent("Creating time windows...", "window_creation")

        windows = create_time_windows(df_final, config.time_window_minutes)

        logger.info(
            "Time windows created",
            window_count=len(windows),
            window_size_minutes=config.time_window_minutes,
            avg_records_per_window=round(len(df_final) / len(windows), 1) if len(windows) > 0 else 0,
        )
        yield WindowCreationEvent(
            f"Created {len(windows)} time windows",
            window_count=len(windows),
            window_size_minutes=config.time_window_minutes,
        )

        logger.debug("Step 5: Starting window analysis", total_windows=len(windows))
        total_windows = len(windows)
        tower_jumps_detected = 0

        for i, (window_start, window_end) in enumerate(windows, 1):
            if i % 500 == 0 or i == 1:
                logger.debug(
                    "Window analysis progress",
                    current_window=i,
                    total_windows=total_windows,
                    tower_jumps_so_far=tower_jumps_detected,
                    progress_pct=round((i / total_windows) * 100, 1),
                )

            interval = analyze_time_window(df_final, window_start, window_end, config)

            if interval:
                intervals.append(interval)

                if interval.is_tower_jump:
                    tower_jumps_detected += 1
                    logger.debug(
                        "Tower jump detected",
                        window_index=i,
                        start_time=window_start.isoformat(),
                        end_time=window_end.isoformat(),
                        estimated_state=interval.estimated_state,
                        confidence=round(interval.confidence * 100, 1),
                        record_count=interval.record_count,
                    )

                yield AnalysisProgressEvent(
                    f"Analyzed window {i}/{total_windows}: {interval.estimated_state}",
                    current_window=i,
                    total_windows=total_windows,
                    estimated_state=interval.estimated_state,
                    is_tower_jump=interval.is_tower_jump,
                )

                yield IntervalCompletedEvent(
                    f"Completed interval {window_start.strftime('%H:%M')} - {window_end.strftime('%H:%M')}",
                    interval_data={
                        "start_time": window_start.isoformat(),
                        "end_time": window_end.isoformat(),
                        "estimated_state": interval.estimated_state,
                        "is_tower_jump": interval.is_tower_jump,
                        "confidence": round(interval.confidence * 100, 1),
                        "record_count": interval.record_count,
                    },
                )

            if i % 100 == 0 or i in [1, total_windows // 4, total_windows // 2, total_windows * 3 // 4, total_windows]:
                yield AnalysisProgressEvent(
                    f"Processing progress: {i}/{total_windows} windows analyzed",
                    current_window=i,
                    total_windows=total_windows,
                )

        logger.debug(
            "Step 6: Generating final summary",
            total_intervals=len(intervals),
            tower_jumps_detected=tower_jumps_detected,
        )
        summary = generate_analysis_summary(intervals)

        logger.info(
            "Tower jumps analysis completed successfully",
            total_intervals=len(intervals),
            tower_jumps_detected=tower_jumps_detected,
            tower_jump_percentage=summary.get("tower_jump_percentage", 0),
            most_common_state=summary.get("most_common_state", "Unknown"),
            average_confidence=round(summary.get("average_confidence", 0) * 100, 1),
            processing_efficiency=f"Processed {len(windows)} windows from {len(df)} records",
        )

        yield CompletionEvent(
            "Analysis completed successfully",
            summary=summary,
            total_intervals=len(intervals),
            tower_jumps=tower_jumps_detected,
        )

    except Exception as e:
        logger.exception(
            "Analysis failed with exception",
            intervals_processed=len(intervals),
            total_records=len(df),
        )
        yield ErrorEvent(f"Analysis failed: {e!s}", error_type=type(e).__name__, error_details=str(e))
        return []

    return intervals


async def analyze_tower_jumps_stream(df: pd.DataFrame, config: Config):
    logger.info(
        "Starting true streaming tower jumps analysis",
        total_records=len(df),
        time_window_minutes=config.time_window_minutes,
        max_speed_mph=config.max_speed_mph,
        confidence_threshold=config.min_confidence_threshold,
    )

    try:
        generator = analyze_tower_jumps(df, config)

        async_next = sync_to_async(_next_with_stop, thread_sensitive=False)

        while True:
            result = await async_next(generator)
            # Completion case: thread caught StopIteration
            if isinstance(result, tuple) and result and result[0] is _STREAM_SENTINEL:
                final_value = result[1]
                logger.info(
                    "True streaming analysis completed",
                    final_result_count=len(final_value) if final_value else 0,
                )
                break

            # Normal yielded event
            yield result
            await asyncio.sleep(0)

    except Exception as e:
        logger.exception("Error in streaming analysis")
        yield ErrorEvent(f"Analysis error: {e!s}", error_type=type(e).__name__, error_details=str(e))


def analyze_time_window(df: pd.DataFrame, start_time: datetime, end_time: datetime, config: Config) -> TimeInterval:
    window_df = df[(df["utc_datetime"] >= start_time) & (df["utc_datetime"] < end_time)].copy()

    logger.debug(
        "Analyzing time window",
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        records_in_window=len(window_df),
        total_dataframe_size=len(df),
    )

    if window_df.empty:
        logger.debug("Empty time window encountered", start_time=start_time.isoformat(), end_time=end_time.isoformat())
        return TimeInterval(
            start_time=start_time,
            end_time=end_time,
            estimated_state="Unknown",
            is_tower_jump=False,
            confidence=0.0,
            record_count=0,
            states_observed=[],
        )

    states_in_window = window_df[window_df["state"].notna()]["state"].tolist()
    unique_states = list(set(states_in_window))

    logger.debug(
        "Window state analysis",
        start_time=start_time.isoformat(),
        states_in_window=len(states_in_window),
        unique_states=unique_states,
        state_changes=len(unique_states),
    )

    estimated_state = estimate_most_likely_state(window_df)

    is_tower_jump = detect_tower_jump_pattern(window_df, config)

    confidence = calculate_confidence(window_df, estimated_state, config)

    max_distance = window_df["distance_km"].max() if not window_df["distance_km"].empty else 0
    max_speed = window_df["speed_kmh"].max() if not window_df["speed_kmh"].empty else 0

    logger.debug(
        "Window analysis completed",
        start_time=start_time.isoformat(),
        estimated_state=estimated_state,
        is_tower_jump=is_tower_jump,
        confidence=round(confidence * 100, 1),
        max_distance_km=round(max_distance, 2) if pd.notna(max_distance) else None,
        max_speed_kmh=round(max_speed, 2) if pd.notna(max_speed) else None,
    )

    return TimeInterval(
        start_time=start_time,
        end_time=end_time,
        estimated_state=estimated_state,
        is_tower_jump=is_tower_jump,
        confidence=confidence,
        record_count=len(window_df),
        states_observed=unique_states,
        max_distance_km=max_distance if pd.notna(max_distance) else None,
        max_speed_kmh=max_speed if pd.notna(max_speed) else None,
    )


def estimate_most_likely_state(df: pd.DataFrame) -> str:
    if df.empty:
        logger.debug("Cannot estimate state for empty DataFrame")
        return "Unknown"

    state_records = df[df["state"].notna()].copy()

    if state_records.empty:
        logger.debug("No valid state records found for estimation", total_records=len(df))
        return "Unknown"

    # Simple approach: most frequent state
    # TODO: Could be enhanced with duration weighting and coordinate clustering
    state_counts = Counter(state_records["state"])
    most_common_state = state_counts.most_common(1)[0][0]

    logger.debug(
        "State estimation completed",
        total_records=len(df),
        records_with_state=len(state_records),
        state_distribution=dict(state_counts.most_common()),
        estimated_state=most_common_state,
    )

    return most_common_state


def detect_tower_jump_pattern(df: pd.DataFrame, config: Config) -> bool:
    if df.empty or len(df) < 2:
        logger.debug("Insufficient data for tower jump detection", record_count=len(df), min_required=2)
        return False

    unique_states = df[df["state"].notna()]["state"].nunique()

    logger.debug(
        "Tower jump pattern analysis",
        record_count=len(df),
        unique_states=unique_states,
        max_speed_threshold=config.max_speed_kmh,
    )

    if unique_states > 1:
        high_speed_count = (df["speed_kmh"] > config.max_speed_kmh).sum()
        if high_speed_count > 0:
            logger.debug(
                "Tower jump detected: high speed violations",
                high_speed_count=high_speed_count,
                max_speed_observed=df["speed_kmh"].max(),
                speed_threshold=config.max_speed_kmh,
            )
            return True

        anomalous_count = df["is_anomalous"].sum()
        if anomalous_count > 0:
            logger.debug(
                "Tower jump detected: anomalous movements", anomalous_count=anomalous_count, total_records=len(df)
            )
            return True

        state_changes = count_state_changes(df)
        if state_changes > 2:
            logger.debug("Tower jump detected: rapid state changes", state_changes=state_changes, threshold=2)
            return True

    logger.debug(
        "No tower jump pattern detected",
        unique_states=unique_states,
        anomalous_movements=df["is_anomalous"].sum() if "is_anomalous" in df else 0,
        max_speed=df["speed_kmh"].max() if "speed_kmh" in df else 0,
    )
    return False


def count_state_changes(df: pd.DataFrame) -> int:
    if df.empty:
        return 0

    states = df[df["state"].notna()]["state"].tolist()
    if len(states) < 2:
        return 0

    changes = 0
    for i in range(1, len(states)):
        if states[i] != states[i - 1]:
            changes += 1

    return changes


def calculate_confidence(df: pd.DataFrame, estimated_state: str, config: Config) -> float:
    if df.empty:
        logger.debug("Cannot calculate confidence for empty DataFrame")
        return 0.0

    state_records = df[df["state"].notna()]

    if state_records.empty:
        logger.debug("No state records available for confidence calculation", total_records=len(df))
        return 0.0

    estimated_state_count = (state_records["state"] == estimated_state).sum()
    state_consistency = estimated_state_count / len(state_records)

    record_count_factor = min(len(df) / 10.0, 1.0)

    anomaly_count = df["is_anomalous"].sum()
    anomaly_penalty = max(0.0, 1.0 - (anomaly_count / len(df)))

    confidence = (
        config.state_consistency_weight * state_consistency
        + config.record_count_weight * record_count_factor
        + config.duration_weight * anomaly_penalty
    )

    final_confidence = max(0.0, min(1.0, confidence))

    logger.debug(
        "Confidence calculation completed",
        total_records=len(df),
        state_records=len(state_records),
        estimated_state=estimated_state,
        estimated_state_count=estimated_state_count,
        state_consistency=round(state_consistency, 3),
        record_count_factor=round(record_count_factor, 3),
        anomaly_count=anomaly_count,
        anomaly_penalty=round(anomaly_penalty, 3),
        final_confidence=round(final_confidence, 3),
    )

    return final_confidence


def generate_analysis_summary(intervals: list[TimeInterval]) -> dict[str, any]:
    logger.debug("Generating analysis summary", total_intervals=len(intervals))

    if not intervals:
        logger.warning("No intervals provided for summary generation")
        return {}

    total_intervals = len(intervals)
    tower_jump_intervals = sum(1 for interval in intervals if interval.is_tower_jump)

    states_frequency = Counter()
    confidence_scores = []

    for interval in intervals:
        if interval.estimated_state != "Unknown":
            states_frequency[interval.estimated_state] += 1
        confidence_scores.append(interval.confidence)

    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0

    summary = {
        "total_intervals": total_intervals,
        "tower_jump_intervals": tower_jump_intervals,
        "tower_jump_percentage": (tower_jump_intervals / total_intervals * 100) if total_intervals > 0 else 0,
        "most_common_state": states_frequency.most_common(1)[0][0] if states_frequency else "Unknown",
        "average_confidence": avg_confidence,
        "states_observed": list(states_frequency.keys()),
    }

    logger.info(
        "Analysis summary generated",
        total_intervals=total_intervals,
        tower_jump_intervals=tower_jump_intervals,
        tower_jump_percentage=round(summary["tower_jump_percentage"], 1),
        most_common_state=summary["most_common_state"],
        average_confidence_pct=round(avg_confidence * 100, 1),
        unique_states=len(states_frequency),
        state_distribution=dict(states_frequency.most_common(5)),
    )

    return summary
