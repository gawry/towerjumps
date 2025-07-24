from pathlib import Path

import pandas as pd
import structlog

from towerjumps.models import LocationRecord

# Configure structured logging
logger = structlog.get_logger(__name__)


class DataLoadError(Exception):
    """Exception raised when data loading fails."""

    def __init__(self, file_path: Path):
        super().__init__(f"Data file not found: {file_path}")
        self.file_path = file_path


class CsvReadError(Exception):
    """Exception raised when CSV reading fails."""

    def __init__(self, original_error: Exception):
        super().__init__(f"Error reading CSV file: {original_error}")
        self.original_error = original_error


def load_csv_data(file_path: str) -> list[LocationRecord]:
    file_path = Path(file_path)
    if not file_path.exists():
        raise DataLoadError(file_path)

    try:
        df = pd.read_csv(
            file_path,
            dtype={
                "Page": "Int64",
                "Item": "Int64",
                "Latitude": "float64",
                "Longitude": "float64",
                "TimeZone": "string",
                "City": "string",
                "County": "string",
                "State": "string",
                "Country": "string",
                "CellType": "string",
            },
            keep_default_na=True,
            na_values=["", "0", "0.0"],
        )

        logger.info("Data loaded from CSV", file_path=str(file_path), raw_records=len(df))

        datetime_format = "%m/%d/%y %H:%M"
        df["UTCDateTime"] = pd.to_datetime(df["UTCDateTime"], format=datetime_format, errors="coerce")
        df["LocalDateTime"] = pd.to_datetime(df["LocalDateTime"], format=datetime_format, errors="coerce")

        invalid_utc = df["UTCDateTime"].isna().sum()
        if invalid_utc > 0:
            logger.warning("Invalid datetime records detected", invalid_utc_count=invalid_utc, file_path=str(file_path))

        df_valid = df.dropna(subset=["UTCDateTime"]).copy()

        df_valid["LocalDateTime"] = df_valid["LocalDateTime"].fillna(df_valid["UTCDateTime"])

        coordinate_columns = ["Latitude", "Longitude"]
        for col in coordinate_columns:
            df_valid[col] = df_valid[col].replace(0.0, pd.NA)

        df_valid["Page"] = df_valid["Page"].fillna(0)
        df_valid["Item"] = df_valid["Item"].fillna(0)

        df_valid["CellType"] = df_valid["CellType"].fillna("Unknown")

        skipped_rows = len(df) - len(df_valid)

        logger.info(
            "Data processing completed",
            valid_records=len(df_valid),
            skipped_rows=skipped_rows,
            file_path=str(file_path),
        )

        if skipped_rows > 0:
            logger.debug(
                "Records skipped during processing",
                skipped_count=skipped_rows,
                reason="parsing_errors",
                file_path=str(file_path),
            )

        logger.debug("Converting DataFrame to LocationRecord objects", record_count=len(df_valid))
        return dataframe_to_records(df_valid)

    except Exception as e:
        raise CsvReadError(e) from e


def dataframe_to_records(df: pd.DataFrame) -> list[LocationRecord]:
    logger.debug("Starting DataFrame to LocationRecord conversion", total_rows=len(df))

    records = []

    for i, row in enumerate(df.itertuples(index=False), 1):
        if i % 1000 == 0:
            logger.debug(
                "DataFrame conversion progress",
                processed_rows=i,
                total_rows=len(df),
                progress_pct=round((i / len(df)) * 100, 1),
            )
        record = LocationRecord(
            page=int(row.Page) if pd.notna(row.Page) else 0,
            item=int(row.Item) if pd.notna(row.Item) else 0,
            utc_datetime=row.UTCDateTime,
            local_datetime=row.LocalDateTime,
            latitude=row.Latitude if pd.notna(row.Latitude) else None,
            longitude=row.Longitude if pd.notna(row.Longitude) else None,
            timezone=row.TimeZone if pd.notna(row.TimeZone) else None,
            city=row.City if pd.notna(row.City) else None,
            county=row.County if pd.notna(row.County) else None,
            state=row.State if pd.notna(row.State) else None,
            country=row.Country if pd.notna(row.Country) else None,
            cell_type=row.CellType if pd.notna(row.CellType) else "Unknown",
        )
        records.append(record)

    logger.debug("DataFrame to LocationRecord conversion completed", total_records=len(records))
    return records


def validate_data(records: list[LocationRecord]) -> dict[str, any]:
    logger.debug("Starting data validation", total_records=len(records))

    stats = {
        "total_records": len(records),
        "records_with_location": 0,
        "records_without_location": 0,
        "unique_states": set(),
        "date_range": None,
        "cell_types": set(),
    }

    if not records:
        logger.warning("No records provided for validation")
        return stats

    # Calculate statistics
    dates = []
    for i, record in enumerate(records, 1):
        if i % 5000 == 0:
            logger.debug(
                "Validation progress",
                processed_records=i,
                total_records=len(records),
                progress_pct=round((i / len(records)) * 100, 1),
            )
        if record.has_location:
            stats["records_with_location"] += 1
        else:
            stats["records_without_location"] += 1

        if record.state:
            stats["unique_states"].add(record.state)

        stats["cell_types"].add(record.cell_type)
        dates.append(record.utc_datetime)

    if dates:
        dates.sort()
        stats["date_range"] = (dates[0], dates[-1])

    logger.info(
        "Data validation completed",
        total_records=stats["total_records"],
        records_with_location=stats["records_with_location"],
        records_without_location=stats["records_without_location"],
        unique_states_count=len(stats["unique_states"]),
        unique_cell_types_count=len(stats["cell_types"]),
        date_range_start=stats["date_range"][0].isoformat() if stats["date_range"] else None,
        date_range_end=stats["date_range"][1].isoformat() if stats["date_range"] else None,
    )

    return stats
