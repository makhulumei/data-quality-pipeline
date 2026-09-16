# Data Quality Pipeline

A clean-room, schema-driven Python pipeline for normalizing, validating, deduplicating, and profiling tabular data. It demonstrates production-minded ETL, Pandas, Pydantic, FastAPI, SQLAlchemy/PostgreSQL, automated tests, packaging, and containerization using only deterministic synthetic data.

## At a glance

| Area | Release behavior |
| --- | --- |
| Inputs | CSV, XLSX, and JSON |
| Rules | Types, required/nullability, uniqueness, ranges, allowed values, and regular expressions |
| Interfaces | Python API, `dq-pipeline` CLI, and FastAPI `/v1/process` |
| Outputs | Normalized DataFrame, structured issues, column profile, and stage timings |
| Persistence | Optional caller-controlled SQLAlchemy write; PostgreSQL is the intended target |
| Verification | Ruff, 45 local tests, 93.55% branch coverage, PostgreSQL integration test, and CI on Python 3.11–3.13 |
| Evidence | Machine-readable 1,010,000-input-row synthetic benchmark with code and environment metadata |

No employer code, client data, production schema, or private business logic is used. The project does not assign a universal “quality score”; fitness for use depends on domain rules and review of the reported issues.

## What it does

- parses CSV, XLSX, and JSON inputs;
- rejects unknown or contradictory schema settings;
- normalizes strings, integers, floats, booleans, and UTC datetimes;
- distinguishes source nulls from failed type coercions;
- removes duplicates with a declared subset and reports missing subset columns safely;
- checks required columns, nullability, uniqueness, ranges, allowed values, and patterns;
- profiles dtypes, nulls, distinct values, duplicate values, and ranges;
- returns stable issue codes, counts, bounded source-row samples, and stage timings;
- exposes one core pipeline through Python, a CLI, and FastAPI;
- supports an explicit, transaction-scoped database write after the caller reviews the result.

## Architecture

```mermaid
flowchart LR
    F[CSV / XLSX / JSON] --> R[Input reader]
    S[JSON schema] --> V[Pydantic configuration validation]
    R --> P[DataQualityPipeline]
    V --> P
    P --> N[Type and text normalization]
    N --> D[Duplicate handling]
    D --> Q[Data-rule validation]
    Q --> G[Column profiling]
    G --> O[PipelineResult: data + report + timings]
    CLI[CLI] --> R
    API[FastAPI] --> R
    PY[Python caller] --> P
    O --> C{Caller approves write?}
    C -->|Optional explicit call| DB[(SQL database)]
```

Persistence is outside `DataQualityPipeline.run()`. The caller decides whether a result is acceptable before calling `write_dataframe`; the library does not automatically block a write because issues exist. See [the architecture contract](docs/architecture.md).

## Quick start

Requirements: Python 3.11–3.13.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip==26.2.1
python -m pip install --requirement requirements-dev.lock
python -m pip install --no-deps --no-build-isolation -e .
pytest -m "not integration" --cov=data_quality_pipeline --cov-report=term-missing
```

Generate a deterministic sample and process it:

```bash
python scripts/generate_synthetic_data.py \
  --rows 10000 \
  --seed 42 \
  --output sample_data/customers.csv

dq-pipeline sample_data/customers.csv \
  --schema sample_data/customer_schema.json \
  --output sample_outputs/customers_cleaned.csv \
  --report sample_outputs/customer_quality_report.json
```

## Schema example

```json
{
  "columns": {
    "customer_id": {
      "dtype": "integer",
      "required": true,
      "nullable": false,
      "unique": true,
      "minimum": 1
    },
    "email": {
      "dtype": "string",
      "nullable": false,
      "lowercase": true,
      "pattern": "^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$"
    }
  },
  "allow_extra_columns": false,
  "drop_duplicate_rows": true,
  "duplicate_subset": ["customer_id"]
}
```

Unknown fields such as `minumum` are rejected. A `duplicate_subset` must be nonempty and reference declared schema columns. If a declared duplicate key is absent from an uploaded dataset, the result contains `missing_duplicate_column` and `missing_column` issues instead of raising an uncontrolled Pandas exception.

## Python use

```python
import pandas as pd

from data_quality_pipeline.models import DatasetSchema
from data_quality_pipeline.pipeline import DataQualityPipeline, PipelineConfig

schema = DatasetSchema.model_validate(
    {
        "columns": {
            "id": {"dtype": "integer", "required": True, "nullable": False},
            "email": {"dtype": "string", "lowercase": True},
        }
    }
)
frame = pd.DataFrame([{"id": "1", "email": " User@Example.COM "}])
result = DataQualityPipeline(PipelineConfig(schema=schema)).run(frame)

print(result.cleaned_data)
print(result.report.model_dump())
```

## FastAPI

Start the service:

```bash
uvicorn data_quality_pipeline.api:app --reload
```

Open `http://localhost:8000/docs`, or submit a multipart request:

```bash
curl -X POST http://localhost:8000/v1/process \
  -F 'file=@sample_data/customers.csv' \
  -F 'schema=<sample_data/customer_schema.json'
```

Response outline:

```json
{
  "report": {
    "rows_received": 10100,
    "rows_output": 10000,
    "columns_received": 7,
    "duplicate_rows_removed": 100,
    "issues": [],
    "profile": {}
  },
  "timings_ms": {
    "transform": 0.0,
    "validation": 0.0,
    "profiling": 0.0,
    "total": 0.0
  },
  "cleaned_preview": []
}
```

Preview rows are disabled by default. Set `MAX_PREVIEW_ROWS` from 1 to 20 only where returning row data is appropriate. `MAX_UPLOAD_MB` defaults to 50 and `MAX_XLSX_EXPANDED_MB` defaults to 200.

## PostgreSQL output

Persistence is opt-in and is never called automatically by the pipeline:

```python
from data_quality_pipeline.database import write_dataframe

if not any(issue.severity == "error" for issue in result.report.issues):
    rows_written = write_dataframe(result.cleaned_data, "clean_customers")
```

Set `DATABASE_URL` from [.env.example](.env.example). `write_dataframe` validates the table identifier and performs each append in one SQLAlchemy transaction. It does not implement idempotency, upserts, migrations, or an application-level approval policy.

Run the real PostgreSQL integration test against an isolated database:

```bash
export TEST_DATABASE_URL='postgresql+psycopg://dq_user:dq_password@localhost:5432/data_quality' # pragma: allowlist secret
pytest -m integration
```

The test verifies connectivity, a successful write and row count, and rollback of a failing batch with no partial insert.

## Docker

```bash
docker compose up --build
```

The API listens on `http://localhost:8000`; PostgreSQL is available to the API service. The image uses a pinned Python 3.12 patch release, upgrades pip to the audited version, and runs as an unprivileged user.

## Tests, package, and quality checks

```bash
ruff check .
pytest -m "not integration" --cov=data_quality_pipeline --cov-report=term-missing
python -m build --no-isolation
```

Coverage must remain at or above 90%. CI runs lint, unit/API tests on Python 3.11, 3.12, and 3.13, a PostgreSQL service test, a wheel smoke test, and a container build.

## Reproducible benchmark

```bash
python scripts/run_benchmark.py \
  --rows 1000000 \
  --repeats 3 \
  --seed 42 \
  --output benchmark_results/benchmark_1000000_rows.json
```

The release record captures the full command, generator and schema identity, Git commit and dirty state, Python/library versions, hardware, peak process memory, warmup policy, requested and actual rows, duplicate/output counts, every run, summary timings, scope, and exclusions. The benchmark times only in-memory normalization, deduplication, validation, and profiling; generation, parsing, upload, network, and database writes are excluded. See [the benchmark method](docs/benchmark-methodology.md).

### Release result

On the clean source revision `40f9a88dc0409744d06ab3798a070a83a2a6a708`, the pipeline processed 1,010,000 synthetic input rows (1,000,000 requested unique rows plus 10,000 controlled duplicates) to 1,000,000 output rows in a median **7.772 seconds** over three runs. The range was 4.412–8.573 seconds with no warmup.

The run used Python 3.13.2, Pandas 2.3.3, NumPy 2.5.3, and Pydantic 2.13.5 on an Apple M2 MacBook Pro (`Mac14,7`) with 8 logical cores, 8 GiB RAM, and macOS 26.3. Peak process RSS was 1,034.67 MiB and includes process overhead and generated frames. Cite only these values with the [machine-readable record](benchmark_results/benchmark_1000000_rows.json) and its stated scope. No comparison with a separate professional workflow is made or implied.

## Security boundaries and limitations

- Processing is in memory; upload size is not a guarantee of peak memory use.
- XLSX is ZIP-based. The API checks declared expanded size, but production deployments should still isolate parsing, scan files, and enforce CPU/memory/time limits.
- User-supplied regular expressions are length-bounded and syntax-checked, but Python regular expressions have no execution timeout here. Restrict schema creation to trusted users and apply request time/rate limits.
- Filenames are reduced to a sanitized basename and omitted from processing logs.
- Preview data is disabled by default; enabling it can expose submitted values to the caller and surrounding observability systems.
- Authentication, authorization, malware scanning, job isolation, object storage, retention controls, metrics, tracing, and secure result delivery are deployment responsibilities.
- Database persistence uses append mode and needs application-specific review, idempotency, conflict handling, and migrations.
- Fuzzy matching and semantic correction are intentionally absent because they require approved domain rules and reference data.
- Performance evidence is synthetic and cannot be generalized to other schemas, distributions, machines, or production workloads.

See [SECURITY.md](SECURITY.md) for the release security model.

## License

MIT. See [LICENSE](LICENSE).
