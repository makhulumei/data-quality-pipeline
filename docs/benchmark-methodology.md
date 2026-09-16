# Benchmark methodology

Benchmark claims are valid only when accompanied by the JSON written by `scripts/run_benchmark.py`.

## Procedure

```bash
python scripts/run_benchmark.py \
  --rows 1000000 \
  --repeats 3 \
  --seed 42 \
  --output benchmark_results/benchmark_1000000_rows.json
```

For repeat `n`, the generator uses `base_seed + n - 1`. Data generation happens before the timer starts. Each timed run creates a new pipeline result from the generated in-memory DataFrame.

## Timed scope

- configured normalization and type coercion;
- duplicate handling;
- structural, coercion, and data-rule validation;
- output-column profiling.

## Excluded scope

- synthetic data generation;
- CSV, XLSX, or JSON serialization and parsing;
- upload and network transfer;
- API framework overhead;
- database writes;
- container startup and UI work.

## Machine-readable evidence

Each record contains:

- UTC generation time;
- full execution command;
- Git commit SHA and dirty-state flag;
- generator version, schema path, and schema SHA-256;
- base seed and per-run seeds;
- requested unique rows, actual input rows, controlled duplicates, and output rows;
- repeat count, warmup policy, scope, and exclusions;
- Python, Pandas, NumPy, and Pydantic versions;
- operating system/platform, machine model, chip/CPU, logical cores, and RAM;
- peak process resident-set high-water mark where the operating system exposes it;
- each elapsed time and throughput plus minimum, median, and maximum duration.

Peak RSS includes the interpreter, generated frame, transformed frames, and other process overhead. It is a high-water mark, not an isolated allocation measurement. A `0.0` value means the platform did not expose the metric through the script’s supported interface.

## Interpretation rules

- Treat the record as evidence for its exact revision, environment, schema, and synthetic distribution.
- Do not compare runs from different revisions as identical experiments.
- Do not extrapolate to other schemas, machines, formats, databases, or production workloads.
- Do not use this result to compare an unrelated implementation or professional workflow.
- Rerun after material changes to pipeline, schema, generator, or pinned dependencies.
