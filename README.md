# Mid-Columbia Events Pipeline

A local event-ingestion pipeline for Tri-Cities weekly Reddit posts and the broader Mission Control event database.

Current status: Cargo Harvester core is being formalized from the earlier prototype ZIPs.

## Windows setup

Use Python 3.13 for this project. Python 3.14 is currently too new for parts of the dependency chain.

```cmd
setup_windows.bat
```

Then harvest a week:

```cmd
run_harvester.bat 2026-07-01 2026-07-07
```

The old prototype launcher is obsolete:

```cmd
cargo_harvester_gui.py
```

The current entry point is:

```cmd
python -m cargo_harvester.cli
```

After editable install, this also works:

```cmd
cargo-harvester
```

## Tests

```cmd
run_tests.bat
```

Direct command after setup:

```cmd
python -m unittest discover -s tests -p "test_*.py"
```

## Python version note

Pinned to Python `>=3.13,<3.14` until the packaging/browser dependency chain is validated on Python 3.14.
