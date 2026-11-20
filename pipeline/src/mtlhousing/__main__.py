"""Pipeline entry point: `python -m mtlhousing <step>`."""

from __future__ import annotations

import argparse


def step_boundaries() -> None:
    from mtlhousing import boundaries, config

    q = boundaries.load_quartiers()
    path = boundaries.write_quartiers(q, config.QUARTIERS_PARQUET)
    print(
        f"{len(q)} quartiers, {q['municipality'].nunique()} municipalities, "
        f"{q['dwellings'].sum():,} dwellings -> {path}"
    )


STEPS = {"boundaries": step_boundaries}


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m mtlhousing")
    parser.add_argument("step", choices=sorted(STEPS))
    STEPS[parser.parse_args().step]()


if __name__ == "__main__":
    main()
