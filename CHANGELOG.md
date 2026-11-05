# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) (`MAJOR.MINOR.PATCH`). The version in
`pyproject.toml` matches the latest released version below.

## [Unreleased]

## [0.1.1] - 2026-11-05

### Added

- `CHANGELOG.md` with semantic versioning, and a rule in `AGENTS.md` to record every change here and
  keep the `pyproject.toml` version in sync.

### Changed

- Project instructions moved from `CLAUDE.md` to `AGENTS.md`; `CLAUDE.md` imports them with
  `@AGENTS.md` ([#2](https://github.com/jussipalanen/jala-forest-ai/pull/2)).

## [0.1.0] - 2026-11-05

Phase 1: data import and PostGIS analysis
([#1](https://github.com/jussipalanen/jala-forest-ai/pull/1)).

### Added

- PostGIS 17 / 3.5 service in Docker Compose (`localhost:5433`) and a `./dev` helper script
  (`up`, `down`, `restart`, `logs`, `ps`, `psql`, `reset`, `run`, `test`).
- Paged WFS 2.0 client for the Metsäkeskus `v2:stand` layer and Syke's Natura 2000 layers (SAC, SPA,
  SCI), with checks for completeness, duplicate ids and the EPSG:3067 response CRS.
- GeoPandas import into PostGIS for the study area Noljakka, Joensuu. Each source is swapped
  atomically and logged in `import_runs` with its fetch time and content hash; a failed import keeps
  the previous version.
- Natura 2000 overlap per forest stand in hectares and percent, computed in EPSG:3067. Overlapping
  Natura sites count once and boundary-only contact adds no area.
- GeoParquet export (EPSG:4326) with the source and fetch time per stand.
- `jalaforest` CLI: `import`, `analyze`, `export`, `run`, `fingerprint`, `crosscheck`.
- Tests: synthetic overlap cases, import failure handling and WFS paging.
- README with verified setup, import and check commands.

[Unreleased]: https://github.com/jussipalanen/jala-forest-ai/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/jussipalanen/jala-forest-ai/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jussipalanen/jala-forest-ai/releases/tag/v0.1.0
