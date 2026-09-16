# Security and data handling

## Repository scope

This is a clean-room portfolio project. It contains deterministic synthetic data and general-purpose implementation code. It must not contain employer/client code, confidential schemas, credentials, private endpoints, personal records, licensed datasets, or production-derived samples.

## Implemented controls

- Uploaded bodies are capped by `MAX_UPLOAD_MB` (50 MB by default).
- XLSX archive members are checked against `MAX_XLSX_EXPANDED_MB` (200 MB by default) before parsing.
- Supported upload suffixes are limited to `.csv`, `.xlsx`, and `.json`.
- Unknown schema fields, invalid regular expressions, and contradictory configuration are rejected.
- Regular-expression patterns are limited to 512 characters.
- Upload names are reduced to a sanitized basename and are not included in processing log messages.
- Row previews are disabled by default and capped at 20 when deliberately enabled.
- Validation messages contain issue metadata and bounded row indexes, not raw row values.
- Database table names must be simple SQL identifiers, and each append runs in one transaction.
- Runtime and development dependencies are pinned separately for repeatable verification.

## Explicit boundaries

The service processes data in memory. Compressed and parsed representations can use substantially more memory than the upload. Archive metadata can be deceptive, and Python regular expressions can consume excessive CPU for adversarial input because this implementation has no regex timeout. Treat schema creation as a trusted operation.

Before production use, add authentication and authorization, rate/request deadlines, process-level CPU and memory isolation, malware/content scanning, secure object storage, encrypted transport/storage, retention/deletion rules, structured audit events, dependency/container scanning, and monitoring. Do not log raw records. Review domain rules and legal requirements before handling personal or regulated data.

Database persistence is an explicit caller action. The helper does not evaluate validation issues, prevent an operator from writing invalid records, implement upserts, or manage schema migrations.

## Reporting a vulnerability

Use the private vulnerability-reporting channel provided by the repository host or contact the repository owner privately. Include affected version, reproduction steps, and impact without including confidential data or live credentials. Do not open a public issue for an unpatched vulnerability.
