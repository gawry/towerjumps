from datetime import datetime, timedelta

import numpy as np
import pandas as pd


def haversine_distance(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    """
    Vectorized haversine distance calculation between arrays of coordinates.
    Returns distances in kilometers.
    """
    lat1_rad = np.radians(lat1)
    lon1_rad = np.radians(lon1)
    lat2_rad = np.radians(lat2)
    lon2_rad = np.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_rad) * np.cos(lat2_rad) * np.sin(dlon / 2) ** 2
    c = 2 * np.arcsin(np.sqrt(a))

    earth_radius_km = 6371.0

    return earth_radius_km * c


def add_distances_and_speeds(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pure function that returns a new DataFrame with distance and speed calculations.
    Does not mutate the input DataFrame.
    """
    result_df = df.copy()

    result_df = result_df.sort_values("utc_datetime").reset_index(drop=True)

    n = len(result_df)
    distances = np.zeros(n)
    speeds = np.zeros(n)
    time_diffs = np.zeros(n)

    if n > 1:
        lat1 = result_df["latitude"].iloc[:-1].values
        lon1 = result_df["longitude"].iloc[:-1].values
        lat2 = result_df["latitude"].iloc[1:].values
        lon2 = result_df["longitude"].iloc[1:].values

        distances[1:] = haversine_distance(lat1, lon1, lat2, lon2)

        time_diff_series = (result_df["utc_datetime"].iloc[1:] - result_df["utc_datetime"].iloc[:-1]).dt.total_seconds()
        time_diffs_seconds = time_diff_series.values
        if len(time_diffs_seconds) != n - 1:
            time_diffs_seconds = time_diffs_seconds[: n - 1]
        time_diffs[1:] = time_diffs_seconds / 3600.0

        mask = time_diffs[1:] > 0
        speeds[1:][mask] = distances[1:][mask] / time_diffs[1:][mask]

    return result_df.assign(distance_km=distances, time_diff_hours=time_diffs, speed_kmh=speeds)


def create_time_windows(df: pd.DataFrame, window_minutes: int) -> list[tuple[datetime, datetime]]:
    if df.empty:
        return []

    frequency = f"{window_minutes}min"
    grouped = df.groupby(pd.Grouper(key="utc_datetime", freq=frequency))

    windows = []
    for group_key, group_data in grouped:
        if not group_data.empty:
            window_start = group_key
            window_end = window_start + timedelta(minutes=window_minutes)
            windows.append((window_start, window_end))

    return windows


def filter_dataframe_with_location(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filter DataFrame to include only records with valid location data.
    Equivalent to LocationRecord.has_location property check.
    """
    has_location_mask = (
        df["latitude"].notna() & df["longitude"].notna() & (df["latitude"] != 0) & (df["longitude"] != 0)
    )
    return df[has_location_mask].copy()


def add_anomaly_detection(df: pd.DataFrame, max_speed_kmh: float, min_distance_km: float) -> pd.DataFrame:
    """
    Pure function that returns a new DataFrame with anomaly detection.
    Does not mutate the input DataFrame.
    """
    is_anomalous = (df["speed_kmh"] > max_speed_kmh) | (
        (df["distance_km"] > min_distance_km) & (df["time_diff_hours"] < 0.1)
    )

    return df.assign(is_anomalous=is_anomalous)
