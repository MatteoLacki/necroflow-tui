# necroflow-tui

Live [panelview](https://github.com/MatteoLacki/panelview) TUI for [necroflow](https://github.com/MatteoLacki/necroflow) pipelines. Each job gets its own browser-style tab showing stdout and stderr as they arrive, with output also teed to the usual `job.log`.

## Install

Requires local checkouts of both `necroflow` and `panelview`:

```bash
make    # creates .venv and installs all three packages editable
```

Or manually:

```bash
python3 -m venv .venv
.venv/bin/pip install -e ../nectroflow/necroflow -e ../panelview -e .
```

## Try it

```bash
make example
```

Runs the necroalchemy grid example (6 pipeline combos) from necroflow with a live TUI.

## CLI

`necroflow-tui` is a drop-in replacement for the `necroflow` CLI — same flags, same TOML format, same output layout:

```bash
necroflow-tui --outdir /results job.toml
necroflow-tui --outdir /results job.toml -c 8 --keep-going
necroflow-tui --outdir /results job.toml --dry-run   # no TUI, just plan
```

## Python API

```python
from necroflow import DAG
from necroflow_tui import execute

dag = DAG(outdir)
for config in configs:
    dag.add(build_pipeline(config))

execute(dag, dag.outdir)                           # same kwargs as necroflow.executor.execute()
execute(dag, dag.outdir, keep_going=True)
execute(dag, dag.outdir, resource_caps={"threads": 8, "ram": 64 * 2**30})
```

## How it works

- `execute()` runs the panelview TUI on the main thread (required by Python's signal handling)
- necroflow's executor runs in a background thread via `PanelRunner.run_with()`
- When a job is submitted, a passive panelview tab is created for it
- The job's subprocess stdout/stderr are teed to both the tab and `job.log`
- Tab title shows `rule_name [fingerprint]`; gains `[done 0]` or `[failed N]` on exit

## Keys

Inherited from panelview:

| Key | Action |
|-----|--------|
| `Shift+←` / `Shift+→` | Switch tabs |
| `Shift+↓` | Enter stream-select mode (choose stdout/stderr) |
| `Shift+↑` | Return to tab mode |
| `↑` `↓` `PgUp` `PgDn` | Scroll output |
| `Ctrl+C` | Open stop menu |
| `Ctrl+X` | Close current tab |
