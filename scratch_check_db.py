import sqlite3, json

conn = sqlite3.connect('/app/storage/hisabhparakh.db')
c = conn.cursor()
c.execute('SELECT id, created_at, storage_key FROM datasets ORDER BY created_at DESC LIMIT 5')
datasets = c.fetchall()
print("DATASETS:")
for d in datasets:
    print(d)

if datasets:
    latest_ds = datasets[0][0]
    print(f"\nSource rows for latest dataset {latest_ds}:")
    c.execute('SELECT physical_row, payload FROM source_rows WHERE dataset_id = ? ORDER BY physical_row LIMIT 10', (latest_ds,))
    for row in c.fetchall():
        payload = row[1] if isinstance(row[1], dict) else json.loads(row[1])
        signals = {s['name']: s['value'] for s in payload.get('signals', [])}
        print(f"Row {row[0]}: signals={signals.get('narration', '')[:100]} | has_ignore={'ignore' in json.dumps(payload).lower()}")

    print("\nPredictions for latest dataset:")
    c.execute('SELECT predictions.transaction_id, predictions.payload FROM predictions JOIN jobs ON jobs.id = predictions.job_id WHERE jobs.dataset_id = ? LIMIT 10', (latest_ds,))
    for row in c.fetchall():
        p = json.loads(row[1]) if row[1] else {}
        print(f"Tx {row[0]}: status={p.get('status')} reasons={p.get('reason_codes')}")
