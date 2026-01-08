"""CLI runner for hyperparameter tuning.

Usage: run in the project root. The script will look for
`models/train_data.json` containing `{"X": [...], "y": [...]}`. If not
found it will generate synthetic data and run the tuner with a small
grid. Results are written to `models/tuning_results.json`.
"""

import json
import os
import random

from src.models.hyperparam_tuner import run_grid_search


def _load_data(path: str):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh).get("X"), json.load(fh).get("y")
    return None, None


def _generate_toy(n=200, dim=5):
    X = [[random.random() for _ in range(dim)] for _ in range(n)]
    y = [sum(x) + random.gauss(0, 0.1) for x in X]
    return X, y


def main():
    data_path = os.path.join("models", "train_data.json")
    X, y = _load_data(data_path)
    if X is None or y is None:
        X, y = _generate_toy()

    grid = {"n_estimators": [10, 30], "max_depth": [3, None]}
    out = run_grid_search(X, y, grid, cv=3, out_path=os.path.join("models", "tuning_results.json"))
    print("Tuning complete. Best:", out.get("best"))


if __name__ == "__main__":
    main()
