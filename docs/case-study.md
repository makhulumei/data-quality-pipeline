# Case study: making inconsistent tabular inputs reviewable

## Problem

Operational datasets often arrive as spreadsheets, CSV files, or JSON exports with mixed types, duplicate records, missing fields, inconsistent text, and undocumented assumptions. Manual cleanup is slow and hard to audit, while silent automated correction can hide the reason a value changed or disappeared.

## Approach

This clean-room project uses a declarative Pydantic schema as the processing contract. A deterministic Pandas pipeline:

1. preserves the caller’s source frame;
2. normalizes configured text, numeric, boolean, and datetime values;
3. records failed non-null type conversion separately from original nulls;
4. validates and applies the declared duplicate key;
5. reports structural and data-rule failures with stable codes, counts, and bounded source-row samples;
6. profiles the resulting columns;
7. returns the data, report, and stage timings through Python, a CLI, or FastAPI.

The project deliberately omits a universal quality score. A required-column failure and a value-level range failure do not have a defensible shared business weighting without domain context.

## Persistence boundary

PostgreSQL persistence is optional and explicitly caller-controlled. The core pipeline never writes automatically. `write_dataframe` performs an append within a transaction, but it does not inspect issues or decide that data is approved. A production caller must define its own acceptance policy, idempotency, upsert, migration, and access controls.

## Verification

The automated suite covers normalization, integer/float/boolean/datetime coercion, source-null versus coercion-failure reporting, duplicate configuration and missing keys, required/extra columns, bounds, allowed values, regular expressions, malformed uploads, upload and XLSX expansion limits, API behavior, CLI success/failure, transaction rollback, and source immutability.

CI runs Ruff and unit/API tests across Python 3.11–3.13, exercises PostgreSQL in a service container, builds and installs the wheel, smokes the CLI, and builds the application image. The release benchmark is reproducible from deterministic synthetic data and publishes machine-readable scope, environment, revision, and per-run evidence.

## What it demonstrates

- Python and vectorized Pandas for repeatable ETL;
- strict Pydantic configuration and transparent data-quality issues;
- FastAPI and CLI adapters around one testable core;
- transaction-scoped SQLAlchemy/PostgreSQL integration;
- defensive upload handling with clearly documented boundaries;
- packaging, locked environments, CI, Docker, and evidence-based performance reporting.

## Limits

Processing is in memory. The API is not a complete production upload platform: authentication, malware scanning, sandboxed parsing, request deadlines, rate limiting, object storage, secure result delivery, and retention policy belong in the deployment. Regular expressions are length-bounded and syntax-checked but do not have an execution timeout. The XLSX expanded-size check mitigates obvious archive expansion but is not a substitute for isolated parsing and resource controls.
