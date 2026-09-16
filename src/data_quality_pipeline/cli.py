from __future__ import annotations

import argparse
import json
from pathlib import Path

from .io import read_dataframe
from .models import DatasetSchema
from .pipeline import DataQualityPipeline, PipelineConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean and validate tabular data.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("cleaned.csv"))
    parser.add_argument("--report", type=Path, default=Path("quality-report.json"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    schema = DatasetSchema.model_validate_json(args.schema.read_text(encoding="utf-8"))
    frame = read_dataframe(args.input)
    result = DataQualityPipeline(PipelineConfig(schema=schema)).run(frame)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    result.cleaned_data.to_csv(args.output, index=False)
    args.report.write_text(
        json.dumps(
            {
                "report": result.report.model_dump(mode="json"),
                "timings_ms": result.timings_ms,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
