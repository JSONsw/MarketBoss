"""Model utility functions for saving/loading and evaluation."""

import json

def save_model(model_obj, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"model": "stub"}, f)
