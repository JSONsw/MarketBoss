"""Simple Airflow DAG to run the daily feature monitor.

Place this file under your Airflow DAGs folder (or mount the `scripts/airflow` folder).
The DAG calls the `run()` function from `scripts/daily_feature_monitor.py`.
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator

import sys
import os
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts.daily_feature_monitor import run as run_monitor

default_args = {
    'owner': 'ai-trading-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    dag_id='daily_feature_monitor',
    default_args=default_args,
    schedule_interval='0 6 * * *',
    catchup=False,
) as dag:

    run_task = PythonOperator(
        task_id='run_feature_monitor',
        python_callable=run_monitor,
    )

    run_task
