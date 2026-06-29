"""
necroflow-tui: panelview TUI integration for necroflow pipelines.

Drop-in replacement for necroflow.executor.execute() that shows each job's
stdout/stderr in a live browser-style tab as it runs.

Usage::

    from necroflow_tui import execute
    execute(dag, outdir="/results")

All kwargs are forwarded to necroflow.executor.execute().
"""
from __future__ import annotations

import subprocess
import threading
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from necroflow.pipeline import _GraphBase


def execute(pipeline: "_GraphBase", outdir, **kwargs) -> None:
    """Run a necroflow pipeline with a panelview TUI showing live job output.

    The TUI must own the main thread (Python signal constraint). This function
    blocks until the user closes the TUI window (or all jobs finish and the user
    presses Ctrl+X on remaining tabs).

    All keyword arguments are forwarded to necroflow.executor.execute().
    Do not pass node_runner — it is set internally.
    """
    from panelview import PanelRunner
    from necroflow.executor import execute as _nf_execute

    if "node_runner" in kwargs:
        raise ValueError("necroflow_tui.execute() sets node_runner internally; do not pass it.")

    runner = PanelRunner()

    def _pipeline_thread(pv_runner):
        node_runner = _make_node_runner(pv_runner)
        _nf_execute(pipeline, outdir, node_runner=node_runner, **kwargs)

    runner.run_with(_pipeline_thread)


def _make_node_runner(runner):
    """Return a node_runner that feeds stdout/stderr to a passive panelview tab."""
    from necroflow.dag import resolve_command

    def node_runner(node, log_path: Path) -> None:
        cmd = resolve_command(node)
        shell = isinstance(cmd, str)
        title = _short_title(node)

        writer = runner.add_live_passive(title=title)

        node.path.parent.mkdir(parents=True, exist_ok=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, "w") as log:
            proc = subprocess.Popen(
                cmd,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            def tee(pipe, stream: str) -> None:
                for line in pipe:
                    log.write(line)
                    log.flush()
                    writer.write(stream, line.rstrip("\n"))

            t_out = threading.Thread(target=tee, args=(proc.stdout, "stdout"), daemon=True)
            t_err = threading.Thread(target=tee, args=(proc.stderr, "stderr"), daemon=True)
            t_out.start()
            t_err.start()
            t_out.join()
            t_err.join()
            proc.wait()

        writer.close(proc.returncode)

        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd)

    return node_runner


def _short_title(node) -> str:
    rule_name = node.key.split("/")[0]
    return f"{rule_name} [{node.fingerprint[:8]}]"
