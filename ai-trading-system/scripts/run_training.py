"""Run training pipeline with walk-forward cross-validation."""

import argparse
import os
import sys
import json
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.train_model import train
from src.features.feature_engineering import build_features
from src.data_pipeline.clean_data import clean_data
from src.monitoring.structured_logger import get_logger

logger = get_logger()


def load_data(data_path: str) -> pd.DataFrame:
    """Load data from JSONL file."""
    records = []
    with open(data_path, 'r', encoding='utf-8') as f:
        for line in f:
            records.append(json.loads(line))
    return pd.DataFrame(records)


def main():
    parser = argparse.ArgumentParser(description='Run model training pipeline')
    parser.add_argument('--data', type=str, required=True, help='Path to input data (JSONL)')
    parser.add_argument('--target', type=str, default='return', help='Target variable name')
    parser.add_argument('--n-splits', type=int, default=5, help='Number of walk-forward splits')
    parser.add_argument('--no-walk-forward', action='store_true', help='Disable walk-forward CV')
    parser.add_argument('--model-dir', type=str, default='models', help='Output directory for models')
    
    args = parser.parse_args()
    
    logger.info("training_pipeline_started", data_path=args.data)
    
    # Load data
    print(f"Loading data from {args.data}...")
    df = load_data(args.data)
    logger.info("data_loaded", rows=len(df))
    
    # Clean data
    print("Cleaning data...")
    df_clean = clean_data(df)
    logger.info("data_cleaned", rows=len(df_clean))
    
    # Build features
    print("Building features...")
    records = df_clean.to_dict('records')
    features = build_features(records)
    features_df = pd.DataFrame(features)
    
    # Prepare X and y
    if args.target not in features_df.columns:
        print(f"Error: Target variable '{args.target}' not found in features")
        sys.exit(1)
    
    # Drop rows with missing target
    features_df = features_df.dropna(subset=[args.target])
    
    feature_names = [c for c in features_df.columns if c not in [args.target, 'timestamp', 'symbol']]
    X = features_df[feature_names].fillna(0).values.tolist()
    y = features_df[args.target].tolist()
    
    print(f"Training with {len(X)} samples and {len(feature_names)} features")
    logger.info("features_prepared", n_samples=len(X), n_features=len(feature_names))
    
    # Train model
    print(f"Training model (walk-forward={not args.no_walk_forward}, n_splits={args.n_splits})...")
    result = train(
        X=X,
        y=y,
        feature_names=feature_names,
        use_walk_forward=not args.no_walk_forward,
        n_splits=args.n_splits,
    )
    
    # Print metrics
    if result.get('metrics'):
        print("\nTraining Metrics:")
        metrics = result['metrics']
        if 'avg_val_mse' in metrics:
            print(f"  Avg Validation MSE: {metrics['avg_val_mse']:.6f}")
            print(f"  Std Validation MSE: {metrics['std_val_mse']:.6f}")
            print(f"  Avg Train MSE: {metrics['avg_train_mse']:.6f}")
            print(f"  N Folds: {metrics['n_folds']}")
    
    # Print top features
    if result.get('feature_importance'):
        print("\nTop 10 Features by Importance:")
        for i, imp in enumerate(result['feature_importance'][:10]):
            print(f"  {i+1}. {imp['feature']}: {imp['importance']:.4f}")
    
    print(f"\nModel saved to {args.model_dir}/")
    logger.info("training_pipeline_completed")


if __name__ == '__main__':
    main()
