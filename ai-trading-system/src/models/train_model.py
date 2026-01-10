"""Training entrypoint for models.

Implements walk-forward cross-validation for time-series data and
computes feature importance. Persists trained models and metadata.
"""

import json
import os
import pickle
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

import numpy as np

from src.models import model_utils
from src.models.xgboost_model import train_xgboost
from src.monitoring import dashboard
from src.monitoring.structured_logger import get_logger

logger = get_logger()


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def walk_forward_split(
    X: np.ndarray,
    y: np.ndarray,
    n_splits: int = 5,
    train_size: float = 0.7,
) -> List[Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]]:
    """
    Generate walk-forward train/validation splits for time-series data.
    
    :param X: Feature matrix (n_samples, n_features)
    :param y: Target vector (n_samples,)
    :param n_splits: Number of walk-forward windows
    :param train_size: Proportion of each window used for training
    :return: List of (X_train, X_val, y_train, y_val) tuples
    """
    n_samples = len(X)
    window_size = n_samples // n_splits
    splits = []
    
    for i in range(n_splits):
        # Define window boundaries
        start_idx = i * window_size
        end_idx = min((i + 1) * window_size, n_samples)
        
        if end_idx - start_idx < 2:
            continue
            
        # Split window into train/val
        split_point = start_idx + int((end_idx - start_idx) * train_size)
        
        X_train = X[start_idx:split_point]
        X_val = X[split_point:end_idx]
        y_train = y[start_idx:split_point]
        y_val = y[split_point:end_idx]
        
        if len(X_train) > 0 and len(X_val) > 0:
            splits.append((X_train, X_val, y_train, y_val))
    
    logger.info("walk_forward_splits_created", n_splits=len(splits), window_size=window_size)
    return splits


def train_with_walk_forward(
    X: np.ndarray,
    y: np.ndarray,
    feature_names: List[str],
    n_splits: int = 5,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Train model using walk-forward cross-validation.
    
    :param X: Feature matrix
    :param y: Target vector
    :param feature_names: List of feature names
    :param n_splits: Number of walk-forward windows
    :param params: Model hyperparameters
    :return: Dict with trained model, metrics, and metadata
    """
    logger.info("walk_forward_training_started", n_samples=len(X), n_features=len(feature_names), n_splits=n_splits)
    
    # Generate walk-forward splits
    splits = walk_forward_split(X, y, n_splits=n_splits)
    
    # Track metrics across folds
    val_scores = []
    train_scores = []
    models = []
    
    for fold_idx, (X_train, X_val, y_train, y_val) in enumerate(splits):
        logger.info("training_fold", fold=fold_idx+1, train_size=len(X_train), val_size=len(X_val))
        
        # Train model on this fold
        model, fold_metrics = train_xgboost(X_train, y_train, X_val, y_val, params=params)
        models.append(model)
        
        # Evaluate on train and validation
        train_mse = fold_metrics['train_mse']
        val_mse = fold_metrics['val_mse']
        
        train_scores.append(train_mse)
        val_scores.append(val_mse)
        
        logger.info(
            "fold_completed",
            fold=fold_idx+1,
            train_mse=train_mse,
            val_mse=val_mse
        )
    
    # Use last model (most recent data) as final model
    final_model = models[-1]
    
    # Compute average metrics
    avg_train_mse = np.mean(train_scores)
    avg_val_mse = np.mean(val_scores)
    std_val_mse = np.std(val_scores)
    
    logger.info(
        "walk_forward_completed",
        avg_train_mse=avg_train_mse,
        avg_val_mse=avg_val_mse,
        std_val_mse=std_val_mse
    )
    
    # Compute feature importance and normalize to dict format for downstream use
    try:
        raw_importances = model_utils.compute_feature_importance(X, y, feature_names)
        importances = [
            {"feature": feat, "importance": float(imp)} for feat, imp in raw_importances
        ]
    except Exception as e:
        logger.warning("feature_importance_failed", error=str(e))
        importances = []
    
    # Build result
    result = {
        "model": final_model,
        "metrics": {
            "avg_train_mse": float(avg_train_mse),
            "avg_val_mse": float(avg_val_mse),
            "std_val_mse": float(std_val_mse),
            "n_folds": len(splits),
            "train_scores": [float(s) for s in train_scores],
            "val_scores": [float(s) for s in val_scores],
        },
        "feature_importance": importances,
        "metadata": {
            "n_samples": len(X),
            "n_features": len(feature_names),
            "feature_names": feature_names,
            "timestamp": datetime.utcnow().isoformat(),
            "params": params or {},
        }
    }
    
    return result


def save_model(
    model_result: Dict[str, Any],
    model_dir: str = "models",
    model_name: Optional[str] = None,
) -> str:
    """
    Save trained model and metadata to disk.
    
    :param model_result: Result dict from train_with_walk_forward
    :param model_dir: Directory to save model
    :param model_name: Optional model name (defaults to timestamp)
    :return: Path to saved model
    """
    _ensure_dir(model_dir)
    
    if model_name is None:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        model_name = f"model_{timestamp}"
    
    # Save model pickle
    model_path = os.path.join(model_dir, f"{model_name}.pkl")
    with open(model_path, "wb") as f:
        pickle.dump(model_result["model"], f)
    
    # Save metadata and metrics
    metadata_path = os.path.join(model_dir, f"{model_name}_metadata.json")
    metadata = {
        "metrics": model_result["metrics"],
        "feature_importance": model_result["feature_importance"],
        "metadata": model_result["metadata"],
    }
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    
    # Save feature importance separately for compatibility
    importance_path = os.path.join(model_dir, "feature_importance.json")
    with open(importance_path, "w", encoding="utf-8") as f:
        json.dump({"importances": model_result["feature_importance"]}, f)
    
    # Update dashboard metric
    try:
        dashboard.set_gauge("last_feature_importance_run", __import__("time").time())
    except Exception:
        pass
    
    logger.info("model_saved", model_path=model_path, metadata_path=metadata_path)
    return model_path


def train(
    X: List[List[float]],
    y: List[float],
    feature_names: List[str],
    params: Optional[Dict[str, Any]] = None,
    use_walk_forward: bool = True,
    n_splits: int = 5,
) -> Dict[str, Any]:
    """
    Train model with optional walk-forward cross-validation.
    
    :param X: Feature matrix (list of lists or numpy array)
    :param y: Target vector
    :param feature_names: List of feature names
    :param params: Model hyperparameters
    :param use_walk_forward: Whether to use walk-forward validation
    :param n_splits: Number of walk-forward splits
    :return: Dict with model and metrics
    """
    # Convert to numpy arrays
    X_arr = np.array(X)
    y_arr = np.array(y)
    
    if use_walk_forward:
        result = train_with_walk_forward(X_arr, y_arr, feature_names, n_splits=n_splits, params=params)
    else:
        # Simple training without walk-forward
        model = train_xgboost(X_arr, y_arr, params=params)
        try:
            importances = model_utils.compute_feature_importance(X_arr, y_arr, feature_names)
        except Exception:
            importances = []
        
        result = {
            "model": model,
            "metrics": {},
            "feature_importance": importances,
            "metadata": {
                "n_samples": len(X_arr),
                "n_features": len(feature_names),
                "feature_names": feature_names,
                "timestamp": datetime.utcnow().isoformat(),
                "params": params or {},
            }
        }
    
    # Save model
    save_model(result)
    
    return result


__all__ = ["train", "train_with_walk_forward", "save_model", "walk_forward_split"]
