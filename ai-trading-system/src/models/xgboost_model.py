"""XGBoost model wrapper."""

import xgboost as xgb
import numpy as np
from typing import Dict, Any, Tuple


def build_xgb_model(params: dict = None):
    """Legacy stub for compatibility."""
    return {"type": "xgboost", "params": params}


def train_xgboost(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray = None,
    y_val: np.ndarray = None,
    params: Dict[str, Any] = None
) -> Tuple[xgb.Booster, Dict[str, Any]]:
    """Train an XGBoost model.
    
    Args:
        X_train: Training features
        y_train: Training targets
        X_val: Validation features (optional)
        y_val: Validation targets (optional)
        params: XGBoost parameters (optional)
        
    Returns:
        Tuple of (trained model, training metrics dict)
    """
    if params is None:
        params = {
            'objective': 'reg:squarederror',
            'max_depth': 6,
            'learning_rate': 0.1,
            'n_estimators': 100,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42
        }
    
    # Create DMatrix
    dtrain = xgb.DMatrix(X_train, label=y_train)
    
    # Setup validation if provided
    evals = [(dtrain, 'train')]
    if X_val is not None and y_val is not None:
        dval = xgb.DMatrix(X_val, label=y_val)
        evals.append((dval, 'val'))
    
    # Train
    n_estimators = params.pop('n_estimators', 100)
    evals_result = {}
    
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=n_estimators,
        evals=evals,
        evals_result=evals_result,
        verbose_eval=False
    )
    
    # Calculate metrics
    train_preds = model.predict(dtrain)
    train_mse = float(np.mean((y_train - train_preds) ** 2))
    
    metrics = {'train_mse': train_mse}
    
    if X_val is not None and y_val is not None:
        val_preds = model.predict(dval)
        val_mse = float(np.mean((y_val - val_preds) ** 2))
        metrics['val_mse'] = val_mse
    
    return model, metrics
