from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shlex
import statistics
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd
import pydantic
from generate_synthetic_data import GENERATOR_VERSION, generate

from data_quality_pipeline.models import DatasetSchema
from data_quality_pipeline.pipeline import DataQualityPipeline, PipelineConfig

try:
    import resource
except ImportError:  # pragma: no cover - resource is unavailable on Windows
    resource = None


SCHEMA_PATH = Path("sample_data/customer_schema.json")


def load_schema() -> DatasetSchema:
    return DatasetSchema.model_validate_json(SCHEMA_PATH.read_text(encoding="utf-8"))


def _run_command(*args: str) -> str | None:
    try:
        return subprocess.run(
            args,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def _git_context() -> dict[str, str | bool]:
    commit = _run_command("git", "rev-parse", "HEAD") or "unavailable"
    status = _run_command("git", "status", "--porcelain")
    return {"commit": commit, "working_tree_dirty": bool(status)}


def _hardware_context() -> dict[str, str | int | None]:
    model = None
    chip = platform.processor() or platform.machine() or "unreported"
    memory_bytes: int | None = None
    if sys.platform == "darwin":
        report = _run_command("system_profiler", "SPHardwareDataType") or ""
        values = {}
        for line in report.splitlines():
            if ":" in line:
                key, value = line.strip().split(":", 1)
                values[key] = value.strip()
        model = values.get("Model Identifier") or values.get("Model Name")
        chip = values.get("Chip", chip)
        memory_text = values.get("Memory", "")
        if memory_text.endswith(" GB"):
            memory_bytes = int(memory_text.removesuffix(" GB")) * 1024**3
    else:
        model = platform.node() or None
        try:
            memory_bytes = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        except (AttributeError, OSError, ValueError):
            memory_bytes = None
    return {
        "machine_model": model,
        "cpu_or_chip": chip,
        "logical_core_count": os.cpu_count(),
        "ram_bytes": memory_bytes,
    }


def _peak_rss_mb() -> float:
    if resource is None:
        return 0.0
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024**2 if sys.platform == "darwin" else 1024
    return round(peak / divisor, 2)


def benchmark(rows: int, repeats: int, seed: int, command: str | None = None) -> dict:
    pipeline = DataQualityPipeline(PipelineConfig(schema=load_schema()))
    samples = []
    for repeat in range(repeats):
        sample_seed = seed + repeat
        frame = generate(rows, sample_seed)
        actual_input_rows = len(frame)
        started = perf_counter()
        result = pipeline.run(frame)
        elapsed = perf_counter() - started
        samples.append(
            {
                "repeat": repeat + 1,
                "seed": sample_seed,
                "input_rows": actual_input_rows,
                "output_rows": len(result.cleaned_data),
                "duplicate_rows_removed": result.report.duplicate_rows_removed,
                "elapsed_seconds": round(elapsed, 6),
                "rows_per_second": round(actual_input_rows / elapsed, 2),
            }
        )
    elapsed_values = [sample["elapsed_seconds"] for sample in samples]
    schema_bytes = SCHEMA_PATH.read_bytes()
    first_sample = samples[0]
    return {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "methodology": {
            "dataset": "deterministic synthetic customer records with controlled data defects",
            "generator_version": GENERATOR_VERSION,
            "schema_path": str(SCHEMA_PATH),
            "schema_sha256": hashlib.sha256(schema_bytes).hexdigest(),
            "base_seed": seed,
            "requested_unique_rows": rows,
            "actual_input_rows": first_sample["input_rows"],
            "controlled_duplicate_rows": first_sample["duplicate_rows_removed"],
            "output_rows": first_sample["output_rows"],
            "repeats": repeats,
            "warmup": "none",
            "scope": "in-memory normalization, deduplication, validation, and profiling",
            "excludes": [
                "synthetic data generation",
                "file parsing",
                "file upload",
                "network",
                "database write",
            ],
        },
        "environment": {
            "python": sys.version.split()[0],
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "pydantic": pydantic.__version__,
            "platform": platform.platform(),
            **_hardware_context(),
            "peak_process_rss_mb": _peak_rss_mb(),
            "peak_memory_note": (
                "Process high-water mark; includes generated frames and process overhead."
            ),
        },
        "source": _git_context(),
        "command": command or "programmatic invocation",
        "summary": {
            "median_seconds": round(statistics.median(elapsed_values), 6),
            "minimum_seconds": min(elapsed_values),
            "maximum_seconds": max(elapsed_values),
        },
        "samples": samples,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rows", type=int, default=100_000)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or Path(f"benchmark_results/benchmark_{args.rows}_rows.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = shlex.join(["python", *sys.argv])
    result = benchmark(args.rows, args.repeats, args.seed, command)
    output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))
    print(f"Full benchmark record: {output}")


if __name__ == "__main__":
    main()
