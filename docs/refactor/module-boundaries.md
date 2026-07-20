# Kairos Module Boundaries (Skeleton Phase)

This document defines ownership boundaries for the first modularization step.
No runtime behavior changes are included in this phase.

## Current Runtime Source of Truth

- `src/kairos/main.py` remains the only execution entry and logic owner.
- New modules are boundaries/placeholders only.

## Planned Ownership Mapping

| Target Module | Future Ownership (migrate from `main.py`) |
|---|---|
| `config/constants.py` | UI constants, extension sets, regex, default values |
| `config/rules.py` | fallback chains, skip reason dictionaries, decision priority tables |
| `utils/file_ops.py` | SHA-256, identical checks, unique path generation, safe rename helpers |
| `utils/sys_helpers.py` | display path normalization, Windows title bar API, icon helpers, OS open helpers |
| `utils/logger.py` | plugin warning capture and queue log bridge |
| `metadata/exif_parser.py` | EXIF/date/subsec capture parsing and rational simplification helpers |
| `metadata/video_parser.py` | hachoir-based media date and camera model for video |
| `metadata/geo_engine.py` | geo extraction fallback chain, cache merge/save, batch reverse geocode |
| `metadata/arbiter.py` | SAME_MS/BURST/REPLACE-KEEP arbitration and second-pass rename logic |
| `database/manifest_db.py` | `_manifest_file.json` read/write, display_meta/raw_meta persistence, map-reduce aggregation |
| `database/auditor.py` | strict asserts and ledger-vs-physical validation |
| `reporting/html_builder.py` | monthly report HTML + lightbox generation |
| `reporting/index_builder.py` | root `_index.html`, filetype summary, report table rendering |
| `core/pipeline.py` | threaded processing orchestration and phase sequencing |
| `ui/app.py` | main CTk app window and runtime state management |
| `ui/dialogs.py` | message box and folder selection dialogs |

## Guardrails for Next Phase

- Keep behavior parity while extracting functions.
- Move code in small slices with import shims to avoid regressions.
- Preserve CSV/HTML output schema during migration.
- Defer assert hardening and manifest_db integration to dedicated phases.