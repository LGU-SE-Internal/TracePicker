"""Modern CLI interface for TracePicker using typer."""

from pathlib import Path

import typer
from rcabench_platform.v2.logging import logger
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .algorithms.platform_adapter import run_tracepicker
from .utils.data_loader import load_inject_time

app = typer.Typer(
    name="tracepicker",
    help="TracePicker: Intelligent trace sampling for distributed systems",
    add_completion=False,
)

console = Console()


@app.command()
def run(
    data_folder: Path = typer.Argument(
        ...,
        help="Path to folder containing trace data (parquet files)",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
    output_folder: Path = typer.Option(
        Path("output"), "--output", "-o", help="Output folder for results"
    ),
    buffer_size: int = typer.Option(
        4000, "--buffer-size", "-b", help="Buffer size for trace processing", min=100
    ),
    sample_rate: float = typer.Option(
        0.1, "--sample-rate", "-r", help="Sampling rate (0-1)", min=0.001, max=1.0
    ),
    pool_height: int = typer.Option(
        1000, "--pool-height", "-p", help="Pool height for encoder", min=100
    ),
    combination_count: int = typer.Option(
        100,
        "--combinations",
        "-c",
        help="Number of combinations for optimization",
        min=10,
    ),
    seed: int = typer.Option(
        42, "--seed", "-s", help="Random seed for reproducibility"
    ),
    verbose: bool = typer.Option(
        False, "--verbose", "-v", help="Enable verbose logging"
    ),
):
    """Run TracePicker on trace data."""

    if verbose:
        logger.info("Verbose mode enabled")

    # Display configuration
    config_table = Table(title="TracePicker Configuration")
    config_table.add_column("Parameter", style="cyan")
    config_table.add_column("Value", style="green")

    config_table.add_row("Data Folder", str(data_folder))
    config_table.add_row("Output Folder", str(output_folder))
    config_table.add_row("Buffer Size", str(buffer_size))
    config_table.add_row("Sample Rate", f"{sample_rate:.3f}")
    config_table.add_row("Pool Height", str(pool_height))
    config_table.add_row("Combinations", str(combination_count))
    config_table.add_row("Seed", str(seed))

    console.print(config_table)
    console.print()

    try:
        # Create output folder
        output_folder.mkdir(parents=True, exist_ok=True)

        # Run TracePicker with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running TracePicker...", total=None)

            result = run_tracepicker(
                data_folder=data_folder,
                buffer_size=buffer_size,
                sample_rate=sample_rate,
                pool_height=pool_height,
                combination_count=combination_count,
                seed=seed,
            )

            progress.update(task, description="Processing complete!")

        # Display results
        results_table = Table(title="TracePicker Results")
        results_table.add_column("Metric", style="cyan")
        results_table.add_column("Value", style="green")

        # Get statistics if available
        stats = result.get("statistics", {})

        # Basic results
        results_table.add_row(
            "Total Traces Loaded",
            str(stats.get("total_traces_loaded", result["total_traces"])),
        )
        results_table.add_row(
            "  - Normal Traces", str(stats.get("normal_traces_loaded", "N/A"))
        )
        results_table.add_row(
            "  - Abnormal Traces", str(stats.get("abnormal_traces_loaded", "N/A"))
        )
        results_table.add_row("", "")  # Separator

        results_table.add_row("Sampled Traces", str(result["sampled_traces"]))
        results_table.add_row(
            "  - Normal Sampled", str(stats.get("sampled_normal", "N/A"))
        )
        results_table.add_row(
            "  - Abnormal Sampled", str(stats.get("sampled_abnormal", "N/A"))
        )
        results_table.add_row("", "")  # Separator

        results_table.add_row("Sampling Ratio", f"{result['sampling_ratio']:.3f}")
        if stats.get("normal_sampling_rate") is not None:
            results_table.add_row(
                "  - Normal Rate", f"{stats['normal_sampling_rate']:.3f}"
            )
        if stats.get("abnormal_sampling_rate") is not None:
            results_table.add_row(
                "  - Abnormal Rate", f"{stats['abnormal_sampling_rate']:.3f}"
            )
        results_table.add_row("", "")  # Separator

        # Performance metrics
        results_table.add_row("Processing Time", f"{result['processing_time']:.3f}s")
        results_table.add_row("  - Encoding", f"{result['encoding_time']:.3f}s")
        results_table.add_row("  - Sampling", f"{result['sampling_time']:.3f}s")
        results_table.add_row("  - Other", f"{result['other_time']:.3f}s")

        # Output location if available
        if stats.get("output_directory"):
            results_table.add_row("", "")  # Separator
            results_table.add_row("Output Directory", str(stats["output_directory"]))

        console.print(results_table)

        # Show sampling validation
        sampled_normal = stats.get("sampled_normal", 0)
        sampled_abnormal = stats.get("sampled_abnormal", 0)

        if sampled_normal > 0 and sampled_abnormal > 0:
            console.print(
                "\n✅ Successfully sampled both normal and abnormal traces",
                style="green",
            )
        elif sampled_normal > 0:
            console.print("\n⚠️  Only normal traces were sampled", style="yellow")
        elif sampled_abnormal > 0:
            console.print("\n⚠️  Only abnormal traces were sampled", style="yellow")
        else:
            console.print("\n❌ No traces were sampled", style="red")

        # Save results
        save_results(result, output_folder, data_folder.name)

        console.print(f"\n✅ Results saved to {output_folder}")

    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        logger.error(f"TracePicker failed: {e}")
        raise typer.Exit(1)


@app.command()
def info(
    data_folder: Path = typer.Argument(
        ...,
        help="Path to folder containing trace data",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
    ),
):
    """Show information about the dataset."""

    try:
        # Load environment info if available
        env_file = data_folder / "env.json"
        if env_file.exists():
            inject_time = load_inject_time(data_folder)

            info_table = Table(title="Dataset Information")
            info_table.add_column("Property", style="cyan")
            info_table.add_column("Value", style="green")

            info_table.add_row("Data Folder", str(data_folder))
            info_table.add_row("Injection Time", str(inject_time))

            console.print(info_table)
        else:
            console.print(f"No environment file found in {data_folder}")

        # Check for required files
        required_files = ["normal_traces.parquet", "abnormal_traces.parquet"]

        files_table = Table(title="Required Files")
        files_table.add_column("File", style="cyan")
        files_table.add_column("Status", style="green")

        for file_name in required_files:
            file_path = data_folder / file_name
            status = "✅ Found" if file_path.exists() else "❌ Missing"
            files_table.add_row(file_name, status)

        console.print(files_table)

    except Exception as e:
        console.print(f"❌ Error reading dataset info: {e}", style="red")
        raise typer.Exit(1)


def save_results(result: dict, output_folder: Path, dataset_name: str):
    """Save results to JSON and CSV files."""
    import json

    import pandas as pd

    # Save detailed results as JSON
    json_file = output_folder / f"{dataset_name}_tracepicker_results.json"
    with open(json_file, "w") as f:
        json.dump(result, f, indent=2, default=str)

    # Save sampled trace IDs as CSV
    if result["sampled_trace_ids"]:
        csv_file = output_folder / f"{dataset_name}_sampled_traces.csv"
        df = pd.DataFrame({"trace_id": result["sampled_trace_ids"], "sampled": True})
        df.to_csv(csv_file, index=False)

    # Save summary statistics
    summary_file = output_folder / f"{dataset_name}_summary.csv"
    summary_data = {
        "metric": [
            "total_traces",
            "sampled_traces",
            "sampling_ratio",
            "abnormal_traces",
            "processing_time",
            "encoding_time",
            "sampling_time",
            "other_time",
        ],
        "value": [
            result["total_traces"],
            result["sampled_traces"],
            result["sampling_ratio"],
            result["abnormal_traces"],
            result["processing_time"],
            result["encoding_time"],
            result["sampling_time"],
            result["other_time"],
        ],
    }

    summary_df = pd.DataFrame(summary_data)
    summary_df.to_csv(summary_file, index=False)


if __name__ == "__main__":
    app()
