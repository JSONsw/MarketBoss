from src.data_pipeline import store_data
records = [{"timestamp": "2025-01-01T00:00:00Z", "symbol": "ABC", "open": "10.0", "high": "11.0", "low": "9.5", "close": "10.5", "volume": "100"}]
out='out_test.jsonl'
ok = store_data.validate_and_store(records, schema_path='config/data_schema.yaml', out_path=out)
print('ok=', ok)
print(open(out,'r',encoding='utf-8').read())
