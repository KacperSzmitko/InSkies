# Pre-commit for Python formatting

This project uses pre-commit to format Python code in `src/backend` with Ruff formatter.

## Install

From the repository root:

```powershell
pip install pre-commit
pre-commit install
```

## Run manually

Format staged files via git hook, or run on all matching files:

```powershell
pre-commit run
pre-commit run --all-files
```

Run only the formatter hook:

```powershell
pre-commit run ruff-format --all-files
```
