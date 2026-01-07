# Reusable Build & Test Workflow

This repository includes a reusable GitHub Actions workflow that runs linting and tests.

File: `.github/workflows/reusable-build-and-test.yml` (callable via `workflow_call`).

Usage example (call this from another workflow in the same repository):

```yaml
name: CI (uses reusable)

on:
  push:
    branches: [ main ]

jobs:
  call-build-and-test:
    uses: ./.github/workflows/reusable-build-and-test.yml
    with:
      python-version: '3.11'
      run-lint: true
      requirements-file: requirements.txt
```

Notes:
- The reusable workflow installs `pytest` and `flake8` for the run.
- Adjust `requirements-file` to point to your dependency manifest when needed.
