"""necroflow-tui CLI — same interface as necroflow, but runs jobs in a panelview TUI."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import tomlkit

from necroflow import DAG
from necroflow.cli import _load_factory, _resolve_request, _create_link_outputs
from necroflow.dag import parse_resource, resolve_paths
from necroflow.grid import iter_configs
from necroflow.pipeline import _sinks

from necroflow_tui import execute


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        prog="necroflow-tui",
        description=(
            "Run necroflow pipelines with a live panelview TUI. "
            "Each TOML must contain a '.pipeline' key ('file.py:function'). "
            "Keys ending in __grid are expanded as a parameter grid."
        ),
    )
    parser.add_argument(
        "jobs",
        nargs="+",
        metavar="JOB.toml",
        help="Job TOML file(s).",
    )
    parser.add_argument(
        "--outdir", "-o",
        required=True,
        type=Path,
        metavar="DIR",
        help="Output directory.",
    )
    parser.add_argument(
        "-c",
        dest="cores",
        default="all",
        metavar="N|all",
        help="Thread cap: integer or 'all' (default: all CPUs).",
    )
    parser.add_argument(
        "--constraint",
        action="append",
        default=[],
        dest="constraints",
        metavar="KEY=VALUE",
        help="Resource cap, e.g. --constraint ram=300Mi. Repeatable.",
    )
    parser.add_argument(
        "--keep-going", "-k",
        action="store_true",
        help="Continue past failures and collect all errors at the end.",
    )
    parser.add_argument(
        "--autoclean",
        action="store_true",
        help="Delete orphan outputs and intermediates when no longer needed.",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        dest="dry_run",
        help="Show what would run without executing anything.",
    )

    args = parser.parse_args(argv)

    dag = DAG(args.outdir)
    combos: list[tuple[str, object, list]] = []

    for job_path_str in args.jobs:
        job_path = Path(job_path_str)
        if not job_path.exists():
            raise SystemExit(f"error: job file not found: {job_path}")
        doc = tomlkit.parse(job_path.read_text(encoding="utf-8"))
        for label, config_dict in iter_configs(doc, base_stem=job_path.stem):
            pipeline_spec = config_dict.get(".pipeline")
            if not pipeline_spec:
                raise SystemExit(f"error: job TOML {job_path} has no '.pipeline' key")
            factory = _load_factory(pipeline_spec)
            request_labels = config_dict.get(".requests", None)
            factory_config = {k: v for k, v in config_dict.items() if not k.startswith(".")}
            P = factory(factory_config)
            request = _resolve_request(P, request_labels) if request_labels is not None else _sinks(P)
            dag.add(P, request=request)
            combos.append((label, P, request))

    cores = args.cores.strip()
    resource_caps = {"threads": os.cpu_count() or 1 if cores.lower() == "all" else int(cores)}
    for kv in args.constraints:
        if "=" not in kv:
            raise SystemExit(f"error: --constraint expects KEY=VALUE, got {kv!r}")
        k, v = kv.split("=", 1)
        resource_caps[k.strip()] = parse_resource(v.strip())

    execute(
        dag,
        dag.outdir,
        resource_caps=resource_caps,
        keep_going=args.keep_going,
        autoclean=args.autoclean,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        return

    for _label, pipeline, _nodes in combos:
        resolve_paths(pipeline.nodes, args.outdir)
    _create_link_outputs(args.outdir, combos)


if __name__ == "__main__":
    main()
