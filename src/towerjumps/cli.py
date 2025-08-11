"""
Tower Jumps Analysis Tool

Analyzes mobile carrier data to detect tower jumps and estimate subscriber location
with confidence levels.
"""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

from towerjumps import configure_logging
from towerjumps.analyzer import analyze_tower_jumps, generate_analysis_summary
from towerjumps.config import Config
from towerjumps.events import (
    AnalysisProgressEvent,
    CompletionEvent,
    DataLoadingEvent,
    ErrorEvent,
    EventType,
    IntervalCompletedEvent,
    ProcessingEvent,
    WindowCreationEvent,
)
from towerjumps.loader import load_csv_data, validate_data
from towerjumps.models import TimeInterval

configure_logging(level="ERROR", enable_dev_logging=False)


class AnalysisError(Exception):
    """Custom exception for analysis errors."""

    def __init__(self, error_type: str, message: str):
        self.error_type = error_type
        super().__init__(f"{error_type}: {message}")


class ProgressManager:
    """Manages Rich progress bars and UI updates during analysis."""

    def __init__(self, console: Console, quiet: bool = False):
        self.console = console
        self.quiet = quiet
        self.progress: Optional[Progress] = None
        self.main_task = None
        self.analysis_task = None

    def __enter__(self):
        """Start progress tracking context."""
        if not self.quiet:
            self.progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeElapsedColumn(),
                console=self.console,
                disable=self.quiet,
            )
            self.progress.__enter__()
            self.main_task = self.progress.add_task("Starting analysis...", total=100)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up progress tracking."""
        if self.progress:
            self.progress.__exit__(exc_type, exc_val, exc_tb)

    def update_data_loading(self, event: DataLoadingEvent) -> None:
        """Handle data loading progress updates."""
        if not self.quiet and self.progress:
            if event.data and event.data.get("total_records"):
                self.progress.update(self.main_task, description=f"📊 {event.message}")
                self.console.print(
                    f"  📈 Processed {event.data['records_with_location']:,} / {event.data['total_records']:,} records"
                )
            else:
                self.progress.update(self.main_task, description=f"📊 {event.message}")

    def update_processing(self, event: ProcessingEvent) -> None:
        """Handle processing step progress updates."""
        if not self.quiet and self.progress:
            step_emoji = {
                "dataframe_conversion": "🔄",
                "distance_calculation": "📏",
                "anomaly_detection": "🚨",
                "window_creation": "⏰",
            }.get(event.data["step"], "⚙️")

            self.progress.update(self.main_task, description=f"{step_emoji} {event.message}")
            if event.data.get("progress") == 100.0:
                self.progress.update(self.main_task, advance=15)

    def update_window_creation(self, event: WindowCreationEvent) -> None:
        """Handle window creation progress updates."""
        if not self.quiet and self.progress:
            self.progress.update(self.main_task, description=f"⏰ {event.message}", completed=60)
            self.console.print(
                f"  📊 Created {event.data['window_count']:,} time windows ({event.data['window_size_minutes']} min each)"
            )

        if self.progress:
            self.analysis_task = self.progress.add_task(
                "🔍 Analyzing time windows...", total=event.data["window_count"]
            )

    def update_analysis_progress(self, event: AnalysisProgressEvent) -> None:
        """Handle analysis progress updates."""
        if self.analysis_task is not None and self.progress:
            current = event.data["current_window"]
            total = event.data["total_windows"]

            self.progress.update(
                self.analysis_task, completed=current, description=f"🔍 Analyzing window {current:,}/{total:,}"
            )

            analysis_progress = (current / total) * 35 + 60
            self.progress.update(self.main_task, completed=analysis_progress)

            if not self.quiet and (current % 500 == 0 or current == total) and event.data.get("estimated_state"):
                jump_status = "🔴 Jump" if event.data.get("is_tower_jump") else "✅ Normal"
                self.console.print(f"  📍 Window {current:,}: {event.data['estimated_state']} - {jump_status}")

    def update_completion(self, event: CompletionEvent) -> None:
        """Handle completion progress updates."""
        if self.progress:
            self.progress.update(self.main_task, completed=100, description="✅ Analysis completed")
            if self.analysis_task is not None:
                self.progress.remove_task(self.analysis_task)

        if not self.quiet:
            summary_data = event.data["summary"]
            self.console.print("\n🎯 [bold green]Analysis Summary:[/bold green]")
            self.console.print(f"  📊 Total intervals: {event.data['total_intervals']:,}")
            self.console.print(
                f"  🔴 Tower jumps: {event.data['tower_jumps_detected']:,} ({event.data['tower_jump_percentage']:.1f}%)"
            )
            self.console.print(f"  📍 Most common state: [bold]{summary_data['most_common_state']}[/bold]")

    def handle_error(self, event: ErrorEvent) -> None:
        """Handle error events."""
        if self.progress:
            self.progress.update(self.main_task, description=f"❌ {event.message}")
        self.console.print(f"[red]❌ Error: {event.message}[/red]")
        if event.data.get("error_details"):
            self.console.print(f"[red]   Details: {event.data['error_details']}[/red]")


class ResultCollector:
    """Collects and manages analysis results."""

    def __init__(self):
        self.intervals: list[TimeInterval] = []
        self.tower_jumps_count = 0

    def handle_interval_completed(self, event: IntervalCompletedEvent) -> None:
        """Track completed intervals."""
        if event.data.get("is_tower_jump"):
            self.tower_jumps_count += 1

    def set_final_intervals(self, intervals: list[TimeInterval]) -> None:
        """Set the final intervals result."""
        self.intervals = intervals

    def get_intervals(self) -> list[TimeInterval]:
        """Get the collected intervals."""
        return self.intervals


class AnalysisEventProcessor:
    """Main coordinator for processing analysis events with real-time updates."""

    def __init__(self, console: Console, quiet: bool = False):
        self.console = console
        self.quiet = quiet

    def process_stream(self, records: list, config: Config) -> list[TimeInterval]:
        """Process the analysis stream with real-time progress updates."""
        progress_manager = ProgressManager(self.console, self.quiet)
        result_collector = ResultCollector()

        with progress_manager:
            stream = analyze_tower_jumps(records, config)

            while True:
                try:
                    event = next(stream)
                except StopIteration as e:
                    intervals = e.value if e.value is not None else []
                    result_collector.set_final_intervals(intervals)
                    break

                self._dispatch_event(event, progress_manager, result_collector)

        return result_collector.get_intervals()

    def _dispatch_event(self, event, progress_manager: ProgressManager, result_collector: ResultCollector) -> None:
        """Dispatch events to appropriate handlers."""
        if event.type == EventType.DATA_LOADING:
            progress_manager.update_data_loading(event)

        elif event.type == EventType.PROCESSING:
            progress_manager.update_processing(event)

        elif event.type == EventType.WINDOW_CREATION:
            progress_manager.update_window_creation(event)

        elif event.type == EventType.ANALYSIS_PROGRESS:
            progress_manager.update_analysis_progress(event)

        elif event.type == EventType.INTERVAL_COMPLETED:
            result_collector.handle_interval_completed(event)

        elif event.type == EventType.COMPLETION:
            progress_manager.update_completion(event)

        elif event.type == EventType.ERROR:
            progress_manager.handle_error(event)
            raise AnalysisError(event.data["error_type"], event.message)


console = Console()
app = typer.Typer(
    name="towerjumps",
    help="🗼 Analyze mobile carrier data to detect tower jumps",
    add_completion=False,
    rich_markup_mode="rich",
)


def _exit_with_error() -> None:
    """Exit with error code 1."""
    raise typer.Exit(1)


def write_csv_report(intervals: list[TimeInterval], output_path: str) -> None:
    """Write analysis results to CSV file."""
    output_path = Path(output_path)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "start_time",
        "end_time",
        "estimated_state",
        "is_tower_jump",
        "confidence_percentage",
        "record_count",
        "states_observed",
        "max_distance_km",
        "max_speed_kmh",
    ]

    import csv

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for interval in intervals:
            writer.writerow(interval.to_csv_row())

    console.print(f"✅ Analysis results written to: [bold green]{output_path}[/bold green]")


def print_rich_data_summary(stats: dict[str, any]) -> None:
    """Print a beautiful data summary using Rich."""

    # Create main info table
    info_table = Table(title="📊 Data Summary", show_header=False, box=None)
    info_table.add_column("Metric", style="cyan", width=25)
    info_table.add_column("Value", style="white")

    info_table.add_row("Total records", f"{stats['total_records']:,}")
    info_table.add_row("Records with location", f"[green]{stats['records_with_location']:,}[/green]")
    info_table.add_row("Records without location", f"[dim]{stats['records_without_location']:,}[/dim]")

    if stats["date_range"]:
        start_date, end_date = stats["date_range"]
        date_range = f"{start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}"
        info_table.add_row("Date range", date_range)

    # Create states table
    states_table = Table(title="🗺️  States Observed", show_header=False)
    states_table.add_column("States", style="magenta")

    if stats["unique_states"]:
        states_list = sorted(stats["unique_states"])
        # Group states in rows of 3
        for i in range(0, len(states_list), 3):
            states_row = " • ".join(states_list[i : i + 3])
            states_table.add_row(states_row)

    # Create cell types table
    cell_table = Table(title="📱 Cell Types", show_header=False)
    cell_table.add_column("Types", style="yellow")

    if stats["cell_types"]:
        cell_types = " • ".join(sorted(stats["cell_types"]))
        cell_table.add_row(cell_types)

    # Display all tables in panels
    console.print(Panel(info_table, expand=False, border_style="blue"))
    console.print(Panel(states_table, expand=False, border_style="magenta"))
    console.print(Panel(cell_table, expand=False, border_style="yellow"))


def print_rich_analysis_summary(summary: dict[str, any]) -> None:
    """Print a beautiful analysis summary using Rich."""

    if not summary:
        console.print("[red]❌ No analysis results to display.[/red]")
        return

    # Create results table
    results_table = Table(title="🎯 Analysis Results", show_header=False, box=None)
    results_table.add_column("Metric", style="cyan", width=30)
    results_table.add_column("Value", style="white")

    # Format tower jump percentage with color
    jump_pct = summary["tower_jump_percentage"]
    if jump_pct > 15:
        jump_color = "red"
    elif jump_pct > 8:
        jump_color = "yellow"
    else:
        jump_color = "green"

    results_table.add_row("Time intervals analyzed", f"{summary['total_intervals']:,}")
    results_table.add_row(
        "Tower jumps detected", f"[bold {jump_color}]{summary['tower_jump_intervals']:,}[/bold {jump_color}]"
    )
    results_table.add_row("Tower jump percentage", f"[bold {jump_color}]{jump_pct:.1f}%[/bold {jump_color}]")
    results_table.add_row("Most common state", f"[bold blue]{summary['most_common_state']}[/bold blue]")
    results_table.add_row("Average confidence", f"{summary['average_confidence'] * 100:.1f}%")

    # Create states summary
    states_text = Text()
    for i, state in enumerate(summary["states_observed"]):
        if i > 0:
            states_text.append(" • ")
        states_text.append(state, style="magenta")

    console.print(Panel(results_table, expand=False, border_style="green"))
    console.print(Panel(states_text, title="🗺️ States Analyzed", border_style="magenta"))


@app.command()
def analyze(
    input_file: Path = typer.Argument(  # noqa: B008
        ..., help="Path to the CSV file containing carrier data", exists=True, file_okay=True, dir_okay=False
    ),
    output: Path = typer.Option("tower_jumps_analysis.csv", "--output", "-o", help="Output CSV file path"),  # noqa: B008
    window: int = typer.Option(15, "--window", "-w", help="Time window size in minutes", min=1, max=1440),
    max_speed: float = typer.Option(
        80.0, "--max-speed", "-s", help="Maximum reasonable speed in mph", min=1.0, max=200.0
    ),
    confidence_threshold: float = typer.Option(
        0.5, "--confidence-threshold", "-c", help="Minimum confidence threshold", min=0.0, max=1.0
    ),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress verbose output"),
) -> None:
    """
    🗼 Analyze mobile carrier data to detect tower jumps.

    This tool processes carrier location data to identify periods where
    subscribers appear to jump between cell towers unrealistically fast,
    indicating GPS/triangulation errors rather than actual movement.
    """

    if not quiet:
        console.print(
            Panel.fit(
                "[bold blue]🗼 Tower Jumps Analysis Tool[/bold blue]\n"
                "Analyzing mobile carrier data for location anomalies",
                border_style="blue",
            )
        )

    config = Config(
        time_window_minutes=window,
        max_speed_mph=max_speed,
        max_speed_kmh=max_speed * 1.60934,  # Convert mph to km/h
        min_confidence_threshold=confidence_threshold,
    )

    if not quiet:
        config_table = Table(title="⚙️  Configuration", show_header=False)
        config_table.add_column("Parameter", style="cyan")
        config_table.add_column("Value", style="white")

        config_table.add_row("Input file", str(input_file))
        config_table.add_row("Output file", str(output))
        config_table.add_row("Time window", f"{config.time_window_minutes} minutes")
        config_table.add_row("Max speed", f"{config.max_speed_mph} mph ({config.max_speed_kmh:.1f} km/h)")
        config_table.add_row("Confidence threshold", f"{config.min_confidence_threshold}")

        console.print(Panel(config_table, expand=False, border_style="cyan"))

    try:
        with Progress(
            SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console, disable=quiet
        ) as progress:
            load_task = progress.add_task("📂 Loading data...", total=None)
            df = load_csv_data(str(input_file))
            progress.remove_task(load_task)

            validate_task = progress.add_task("✅ Validating data...", total=None)
            stats = validate_data(df)
            progress.remove_task(validate_task)

            if not quiet:
                print_rich_data_summary(stats)

            if df.empty:
                console.print("[red]❌ No valid records found in input file.[/red]")
                _exit_with_error()

        processor = AnalysisEventProcessor(console, quiet)
        intervals = processor.process_stream(df, config)

        if not intervals:
            console.print("[red]❌ No time intervals generated from analysis.[/red]")
            _exit_with_error()

        if not quiet:
            with Progress(
                SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console
            ) as progress:
                write_task = progress.add_task("💾 Writing results...", total=None)
                write_csv_report(intervals, str(output))
                progress.remove_task(write_task)
        else:
            write_csv_report(intervals, str(output))

        if not quiet:
            summary = generate_analysis_summary(intervals)
            print_rich_analysis_summary(summary)
            console.print(f"\n🎉 [bold green]Analysis complete![/bold green] Results saved to [bold]{output}[/bold]")

    except Exception as e:
        console.print(f"[red]❌ Error during analysis: {e}[/red]")
        if not quiet:
            console.print_exception()
        raise typer.Exit(1) from e


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
