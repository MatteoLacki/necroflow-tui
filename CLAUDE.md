# necroflow-tui — codebase notes

## What it is

Thin bridge between [necroflow](https://github.com/MatteoLacki/necroflow) and [panelview](https://github.com/MatteoLacki/panelview). Replaces necroflow's terminal logging with a live browser-style TUI where each job gets its own tab.

## File map

| File | Role |
|------|------|
| `src/necroflow_tui/__init__.py` | `execute()` — public API; `_make_node_runner()` builds the job runner |
| `src/necroflow_tui/cli.py` | `necroflow-tui` CLI — mirrors `necroflow` CLI, substitutes `execute()` |
| `Makefile` | `make` (venv), `make example` (necroalchemy grid via TUI) |

## How the bridge works

Python's `signal.signal()` requires the main thread, so the panelview TUI must own it. `execute()`:

1. Creates a `PanelRunner`
2. Calls `runner.run_with(_pipeline_thread)` — TUI blocks on main thread; `_pipeline_thread(runner)` runs in a background daemon thread
3. `_pipeline_thread` builds a `node_runner` (via `_make_node_runner`) and calls `necroflow.executor.execute(..., node_runner=node_runner)`
4. For each job the executor submits, `node_runner(node, log_path)` is called from a thread pool thread:
   - Calls `runner.add_live_passive(title)` → creates a passive panelview tab, returns a `PanelWriter`
   - Starts the subprocess with `stdout=PIPE, stderr=PIPE`
   - Two daemon threads tee each stream to both `job.log` and `writer.write(stream, line)`
   - On exit calls `writer.close(returncode)` → updates tab title with done/failed suffix

## Key necroflow hook

`necroflow.executor.execute()` accepts an optional `node_runner` kwarg (added for this integration). Signature: `node_runner(node, log_path) -> None`. Default is `_run_node` (writes both streams to `job.log`).

## Key panelview APIs used

- `PanelRunner.run_with(fn)` — TUI on main thread; `fn(runner)` in background thread
- `PanelRunner.add_live_passive(title)` → `PanelWriter` — creates tab without starting a subprocess
- `PanelWriter.write(stream, line)` — thread-safe; routes to stdout or stderr log
- `PanelWriter.close(returncode)` — marks tab done/failed

## CLI

`necroflow_tui.cli.main()` is a copy of `necroflow.cli.main()` with one substitution: `dag.execute(...)` → `necroflow_tui.execute(dag, dag.outdir, ...)`. It reuses `_load_factory`, `_resolve_request`, `_create_link_outputs` directly from `necroflow.cli`.

## Venv setup

Local editable installs required — necroflow and panelview are not on PyPI:

```bash
pip install -e ../nectroflow/necroflow -e ../panelview -e .
```

The Makefile `$(STAMP)` target does this automatically.

## Example target

`make example` runs from the necroflow source root (via `cd $(NF_SRC)`) so the relative `.pipeline` path in `necroalchemy_job.toml` resolves correctly. Output lands in `necroflow-tui/examples/output/`.
