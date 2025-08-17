"""Result saver for TracePicker sampling results."""

import datetime
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional

import polars as pl
from rcabench_platform.v2.logging import logger


class TracepickerResultSaver:
    """Save TracePicker sampling results to output directory with original files."""

    def __init__(
        self, input_folder: Path, inject_time: Optional[datetime.datetime] = None
    ):
        """Initialize result saver.

        Args:
            input_folder: Original input folder containing data
            inject_time: Injection time for separating normal/abnormal data
        """
        self.input_folder = Path(input_folder)
        self.inject_time = inject_time

    def save_results(self, sampled_trace_ids: List[str], stats: Dict) -> Path:
        """Save sampling results to output directory.

        Args:
            sampled_trace_ids: List of sampled trace IDs
            stats: Statistics about the sampling process

        Returns:
            Path to output directory
        """
        # Create output directory
        output_dir = self.input_folder / "sampled" / "tracepicker"
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Saving TracePicker results to: {output_dir}")

        # Copy original metadata files
        self._copy_metadata_files(output_dir)

        # Filter and save traces
        self._save_filtered_traces(output_dir, set(sampled_trace_ids))

        # Copy other data files (metrics, logs)
        self._copy_other_files(output_dir)

        # Save TracePicker specific statistics
        self._save_statistics(output_dir, sampled_trace_ids, stats)

        logger.info(
            f"Successfully saved TracePicker results with {len(sampled_trace_ids)} traces"
        )
        return output_dir

    def _copy_metadata_files(self, output_dir: Path):
        """Copy metadata files from input to output directory."""
        metadata_files = [
            "env.json",
            "injection.json",
            "notations.json",
            "conclusion.parquet",
            ".finished",
        ]

        for file_name in metadata_files:
            src_file = self.input_folder / file_name
            if src_file.exists():
                dst_file = output_dir / file_name
                shutil.copy2(src_file, dst_file)
                logger.debug(f"Copied metadata file: {file_name}")

    def _save_filtered_traces(self, output_dir: Path, sampled_trace_ids: set):
        """Filter and save traces based on sampled trace IDs."""
        logger.info("Filtering and saving trace data...")

        # Find trace files (handle both direct and subdirectory structure)
        normal_traces_path, abnormal_traces_path = self._find_trace_files()

        if not normal_traces_path or not abnormal_traces_path:
            logger.error("Could not find trace files")
            return

        # Load and filter traces
        normal_traces_lf = pl.scan_parquet(normal_traces_path)
        abnormal_traces_lf = pl.scan_parquet(abnormal_traces_path)

        # Filter by sampled trace IDs
        normal_filtered = normal_traces_lf.filter(
            pl.col("trace_id").is_in(sampled_trace_ids)
        )
        abnormal_filtered = abnormal_traces_lf.filter(
            pl.col("trace_id").is_in(sampled_trace_ids)
        )

        # Save filtered traces
        normal_output = output_dir / "normal_traces.parquet"
        abnormal_output = output_dir / "abnormal_traces.parquet"

        normal_df = normal_filtered.collect()
        abnormal_df = abnormal_filtered.collect()

        normal_df.write_parquet(normal_output)
        abnormal_df.write_parquet(abnormal_output)

        # Log statistics
        normal_spans = normal_df.height
        abnormal_spans = abnormal_df.height
        normal_traces = normal_df["trace_id"].n_unique() if normal_spans > 0 else 0
        abnormal_traces = (
            abnormal_df["trace_id"].n_unique() if abnormal_spans > 0 else 0
        )

        logger.info(f"Saved normal data: {normal_spans} spans, {normal_traces} traces")
        logger.info(
            f"Saved abnormal data: {abnormal_spans} spans, {abnormal_traces} traces"
        )

    def _copy_other_files(self, output_dir: Path):
        """Copy metrics and logs files."""
        logger.info("Copying metrics and logs...")

        other_files = [
            "normal_metrics.parquet",
            "abnormal_metrics.parquet",
            "normal_metrics_histogram.parquet",
            "abnormal_metrics_histogram.parquet",
            "normal_metrics_sum.parquet",
            "abnormal_metrics_sum.parquet",
            "normal_logs.parquet",
            "abnormal_logs.parquet",
        ]

        for file_name in other_files:
            src_file = self._find_file(file_name)
            if src_file and src_file.exists():
                dst_file = output_dir / file_name
                shutil.copy2(src_file, dst_file)
                logger.debug(f"Copied: {file_name}")

    def _save_statistics(
        self, output_dir: Path, sampled_trace_ids: List[str], stats: Dict
    ):
        """Save TracePicker specific statistics."""
        logger.info("Saving TracePicker statistics...")

        # Create comprehensive statistics
        tracepicker_stats = {
            "algorithm": "TracePicker",
            "timestamp": datetime.datetime.now().isoformat(),
            "input_folder": str(self.input_folder),
            "output_folder": str(output_dir),
            "injection_time": self.inject_time.isoformat()
            if self.inject_time
            else None,
            "sampling_results": {
                "total_sampled_traces": len(sampled_trace_ids),
                "sampled_trace_ids": sampled_trace_ids,
            },
            "algorithm_stats": stats,
            "data_distribution": self._analyze_data_distribution(sampled_trace_ids),
        }

        # Save as JSON
        stats_file = output_dir / "tracepicker_stats.json"
        with open(stats_file, "w") as f:
            json.dump(tracepicker_stats, f, indent=2)

        logger.info(f"Saved statistics to: {stats_file}")

    def _analyze_data_distribution(self, sampled_trace_ids: List[str]) -> Dict:
        """Analyze distribution of sampled traces across normal/abnormal periods."""
        if not self.inject_time:
            return {"analysis": "No injection time available"}

        try:
            # Load trace data to analyze distribution
            normal_path, abnormal_path = self._find_trace_files()
            if not normal_path or not abnormal_path:
                return {"analysis": "Could not find trace files"}

            # Count sampled traces in each category
            normal_lf = pl.scan_parquet(normal_path)
            abnormal_lf = pl.scan_parquet(abnormal_path)

            normal_count = (
                normal_lf.filter(pl.col("trace_id").is_in(sampled_trace_ids))
                .select("trace_id")
                .unique()
                .collect()
                .height
            )

            abnormal_count = (
                abnormal_lf.filter(pl.col("trace_id").is_in(sampled_trace_ids))
                .select("trace_id")
                .unique()
                .collect()
                .height
            )

            total_sampled = len(sampled_trace_ids)

            return {
                "normal_traces_sampled": normal_count,
                "abnormal_traces_sampled": abnormal_count,
                "total_sampled": total_sampled,
                "normal_ratio": normal_count / total_sampled
                if total_sampled > 0
                else 0,
                "abnormal_ratio": abnormal_count / total_sampled
                if total_sampled > 0
                else 0,
                "injection_time": self.inject_time.isoformat(),
            }

        except Exception as e:
            logger.warning(f"Could not analyze data distribution: {e}")
            return {"analysis": f"Analysis failed: {e}"}

    def _find_trace_files(self) -> tuple[Optional[Path], Optional[Path]]:
        """Find normal and abnormal trace files."""
        # Try direct path first
        normal_path = self.input_folder / "normal_traces.parquet"
        abnormal_path = self.input_folder / "abnormal_traces.parquet"

        if normal_path.exists() and abnormal_path.exists():
            return normal_path, abnormal_path

        # Try subdirectories
        for subdir in self.input_folder.iterdir():
            if subdir.is_dir():
                sub_normal = subdir / "normal_traces.parquet"
                sub_abnormal = subdir / "abnormal_traces.parquet"

                if sub_normal.exists() and sub_abnormal.exists():
                    return sub_normal, sub_abnormal

        return None, None

    def _find_file(self, filename: str) -> Optional[Path]:
        """Find a file in input folder or subdirectories."""
        # Try direct path first
        direct_path = self.input_folder / filename
        if direct_path.exists():
            return direct_path

        # Try subdirectories
        for subdir in self.input_folder.iterdir():
            if subdir.is_dir():
                sub_path = subdir / filename
                if sub_path.exists():
                    return sub_path

        return None
