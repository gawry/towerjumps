"""
FastAPI service for Tower Jumps Analysis with Server-Sent Events streaming.
"""

import asyncio
import json
import tempfile
from pathlib import Path
from typing import TypedDict

import structlog
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from towerjumps import configure_logging
from towerjumps.analyzer import analyze_tower_jumps_stream
from towerjumps.config import Config
from towerjumps.loader import load_csv_data

logger = structlog.get_logger(__name__)


class AnalysisSummary(TypedDict):
    total_intervals: int
    tower_jump_intervals: int
    tower_jump_percentage: float
    most_common_state: str
    average_confidence: float
    states_observed: list[str]


class AnalysisConfig(BaseModel):
    """Configuration for tower jump analysis."""

    time_window_minutes: int = 60
    max_speed_mph: float = 70.0
    confidence_threshold: float = 0.5


class AnalysisRequest(BaseModel):
    """Request model for analysis."""

    config: AnalysisConfig = AnalysisConfig()


app = FastAPI(
    title="🗼 Tower Jumps Analysis API",
    description="API for analyzing mobile carrier data to detect tower jumps with real-time streaming",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(..., description="CSV file containing carrier data"),  # noqa: B008
    time_window_minutes: int = Form(60, description="Time window size in minutes"),
    max_speed_mph: float = Form(70.0, description="Maximum reasonable speed in mph"),
    confidence_threshold: float = Form(0.5, description="Minimum confidence threshold"),
):
    logger.info(
        "Analysis request received",
        filename=file.filename,
        file_size=file.size,
        time_window_minutes=time_window_minutes,
        max_speed_mph=max_speed_mph,
        confidence_threshold=confidence_threshold,
    )

    if not file.filename.endswith(".csv"):
        logger.error("Invalid file type", filename=file.filename, expected_extension=".csv")
        raise HTTPException(status_code=400, detail="File must be a CSV")

    try:
        content = await file.read()
        logger.debug("File content read successfully", filename=file.filename, content_size=len(content))
    except Exception as e:
        logger.exception("Failed to read uploaded file", filename=file.filename)
        raise HTTPException(status_code=400, detail=f"Failed to read file: {e}") from e

    config = Config(
        time_window_minutes=time_window_minutes,
        max_speed_mph=max_speed_mph,
        max_speed_kmh=max_speed_mph * 1.60934,  # Convert to km/h
        min_confidence_threshold=confidence_threshold,
    )

    logger.debug(
        "Analysis configuration created",
        time_window_minutes=config.time_window_minutes,
        max_speed_mph=config.max_speed_mph,
        max_speed_kmh=config.max_speed_kmh,
        min_confidence_threshold=config.min_confidence_threshold,
    )

    async def event_stream():
        temp_file_path = None
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name

            logger.debug("Temporary file created for analysis", temp_file_path=temp_file_path, file_size=len(content))

            try:
                # Load data
                logger.debug("Loading data from temporary file", temp_file_path=temp_file_path)
                df = load_csv_data(temp_file_path)

                logger.info(
                    "Starting simplified streaming analysis", record_count=len(df), temp_file_path=temp_file_path
                )

                # Use the simplified streaming approach
                event_count = 0
                async for event in analyze_tower_jumps_stream(df, config):
                    event_count += 1
                    event_data = event.to_dict()

                    if event_data["type"] in ["analysis_progress", "interval_completed", "completion"]:
                        logger.debug(
                            "Analysis progress event",
                            event_type=event_data["type"],
                            event_count=event_count,
                            message=event_data.get("message", ""),
                            data_keys=list(event_data.get("data", {}).keys()),
                        )

                    yield f"event: {event_data['type']}\n"
                    yield f"data: {json.dumps(event_data)}\n\n"

                logger.info(
                    "Simplified streaming analysis completed",
                    total_events_sent=event_count,
                    temp_file_path=temp_file_path,
                )

            finally:
                # Clean up temporary file
                if temp_file_path and Path(temp_file_path).exists():
                    Path(temp_file_path).unlink(missing_ok=True)
                    logger.debug("Temporary file cleaned up", temp_file_path=temp_file_path)

        except Exception as e:
            logger.exception("Analysis failed during streaming", temp_file_path=temp_file_path)

            error_data = {
                "type": "error",
                "timestamp": str(asyncio.get_event_loop().time()),
                "message": f"Analysis failed: {e!s}",
                "data": {"error_type": type(e).__name__, "error_details": str(e)},
            }
            yield f"event: {error_data['type']}\n"
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    logger.debug("Health check requested")
    return {"status": "healthy", "service": "tower-jumps-analysis"}


def run_server(host: str = "127.0.0.1", port: int = 8001, reload: bool = True):
    """Run the FastAPI server."""
    configure_logging(level="DEBUG", enable_dev_logging=True)
    logger.info("Starting FastAPI server", host=host, port=port, reload=reload, log_level="debug")
    uvicorn.run("towerjumps.api:app", host=host, port=port, reload=reload, log_level="debug")


def main():
    """CLI entry point for the Tower Jumps Analysis API server."""
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Tower Jumps Analysis API Server")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind to")
    parser.add_argument("--port", "-p", type=int, default=8001, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    # Support environment variables for deployment
    host = os.getenv("HOST", args.host)
    port = int(os.getenv("PORT", args.port))
    reload = args.reload

    run_server(host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
