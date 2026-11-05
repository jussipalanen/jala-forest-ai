"""Command line entry point: ``uv run jalaforest <command>``."""

from __future__ import annotations

import argparse
import sys

from sqlalchemy import text

from . import checks
from .config import EXPORT_PATH, STUDY_AREA
from .db import compute_overlap, get_engine, init_schema
from .export import export_geoparquet
from .importer import import_all


def cmd_import(engine) -> bool:
    init_schema(engine)
    print(f"Alue: {STUDY_AREA.name}, bbox EPSG:3067 {STUDY_AREA.bbox}")
    ok = True
    for o in import_all(engine):
        if o.ok:
            state = "muuttui" if o.changed else "ennallaan"
            print(f"  OK    {o.source}: {o.feature_count} kohdetta, sha256={o.content_sha256[:16]} ({state})")
        else:
            ok = False
            print(f"  VIRHE {o.source}: tuonti epäonnistui, edellinen onnistunut versio säilytetty.\n"
                  f"        {o.error}", file=sys.stderr)
    return ok


def cmd_analyze(engine) -> None:
    with engine.begin() as conn:
        compute_overlap(conn)
        row = conn.execute(text(
            "SELECT count(*), count(*) FILTER (WHERE natura_overlap_ha > 0), "
            "coalesce(sum(natura_overlap_ha), 0) FROM stand_natura_overlap"
        )).one()
    print(f"Laskettu {row[0]} kuviota, joista {row[1]} osuu Natura 2000 -alueelle "
          f"(yhteensä {row[2]:.4f} ha).")


def cmd_export(engine, path: str) -> None:
    gdf = export_geoparquet(engine, path)
    print(f"Viety {len(gdf)} kuviota tiedostoon {path} (EPSG:4326).")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="jalaforest")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="create tables")
    sub.add_parser("import", help="fetch WFS layers into PostGIS")
    sub.add_parser("analyze", help="compute Natura 2000 overlap per stand")
    p_export = sub.add_parser("export", help="write GeoParquet")
    p_export.add_argument("--output", default=EXPORT_PATH)
    p_run = sub.add_parser("run", help="import + analyze + export")
    p_run.add_argument("--output", default=EXPORT_PATH)
    sub.add_parser("fingerprint", help="hash the data tables (re-run check)")
    sub.add_parser("crosscheck", help="compare PostGIS overlap with a Shapely recomputation")
    args = parser.parse_args(argv)

    engine = get_engine()
    match args.command:
        case "init-db":
            init_schema(engine)
        case "import":
            return 0 if cmd_import(engine) else 1
        case "analyze":
            cmd_analyze(engine)
        case "export":
            cmd_export(engine, args.output)
        case "run":
            if not cmd_import(engine):
                print("Analyysiä ja vientiä ei päivitetty, koska tuonti epäonnistui.", file=sys.stderr)
                return 1
            cmd_analyze(engine)
            cmd_export(engine, args.output)
        case "fingerprint":
            for name, value in checks.fingerprint(engine).items():
                print(f"{name}: {value}")
        case "crosscheck":
            result = checks.crosscheck_overlap(engine)
            print(f"Kuvioita {result['stands']}, suurin ero {result['max_abs_diff_ha']:.2e} ha, "
                  f"poikkeamia {len(result['mismatches'])}")
            return 1 if result["mismatches"] else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
