# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html) (`MAJOR.MINOR.PATCH`). The version in
`pyproject.toml` matches the latest released version below.

## [Unreleased]

### Added

- pgAdmin 4 web UI for local development at http://localhost:5050 (localhost only, no login), started by
  `./dev up` and preconfigured with the project database; `./dev dbui` opens it.

## [0.2.0] - 2026-11-05

Phase 2: map and conversational search.

### Added

- Streamlit map app (`app/streamlit_app.py`) that reads the GeoParquet export: a full-height Folium map
  below a header with logo and app name, a floating result card and the search bar at the bottom.
  Light-green forest theme; layouts for desktop, tablet and phone.
- Filters in a header popover: stand area, Natura 2000 rule and Natura share. A stand counts as on a
  Natura 2000 site from 0.01 ha of overlap, which leaves out boundary slivers.
- Per-stand info box on the map and a table of the matching stands in the result card.
- Gemini search (`google-genai`): the model returns structured search filters or a Finnish clarifying
  question, validated with Pydantic. The unfinished conversation is kept in the Streamlit session and
  the summary is built from the search's own numbers.
- Default model `gemini-3.1-flash-lite`, the lowest-cost model available to new API keys, with
  `gemini-3.5-flash-lite` as a fallback when it is overloaded. Requests time out after 20 s.
- `AI_ENABLED=true|false` switch for the AI search; `.env.example` for the settings.
- App container (`Dockerfile`) and an `app` service in Docker Compose. `./dev up` starts both services,
  and `./dev app`, `./dev lint` and `./dev e2e` were added.
- Accessibility: page language, a named map iframe, heading structure, visible focus and named buttons.
- Playwright tests (layout at three screen sizes, filters, zero result, AI switch, axe check, real
  Gemini search) and unit tests for search, the assistant and the app.
- GitHub Actions CI (lint, tests with PostGIS, Playwright, Docker build) and Dependabot.
- README with badges and collapsible sections.

### Fixed

- `./dev restart` removes the containers and creates them again instead of using `--force-recreate`,
  which failed with "container name is already in use" after an interrupted or concurrent recreate.
- Database tests ran in a schema of the real database, so `DROP TABLE IF EXISTS` in the overlap
  script could fall through to `public` and drop the real `stand_natura_overlap` table. Tests now use
  their own `jalaforest_test` database.

## [0.1.1] - 2026-11-05

### Added

- `CHANGELOG.md` with semantic versioning, and a rule in `AGENTS.md` to record every change here and
  keep the `pyproject.toml` version in sync,
  then tag each merged version `vX.Y.Z` and publish it with `gh release`.

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

[Unreleased]: https://github.com/jussipalanen/jala-forest-ai/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/jussipalanen/jala-forest-ai/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/jussipalanen/jala-forest-ai/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/jussipalanen/jala-forest-ai/releases/tag/v0.1.0
