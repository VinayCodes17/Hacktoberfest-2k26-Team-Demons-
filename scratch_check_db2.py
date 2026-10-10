import sqlite3, json

conn = sqlite3.connect('/app/storage/hisabhparakh.db')
c = conn.cursor()
for j_id in ['b6ac5e83-baf9-4eeb-9c30-93ec491b6872', '33b6a109-b08c-43c4-b4c5-00091b7c3044']:
    c.execute('SELECT transaction_id, payload FROM predictions WHERE job_id = ?', (j_id,))
    rows = c.fetchall()
    print(f"\nJOB {j_id} (Total {len(rows)} rows):")
    status_counts = {}
    reasons_list = []
    for tx, p_str in rows:
        p = json.loads(p_str) if p_str else {}
        st = p.get('status')
        status_counts[st] = status_counts.get(st, 0) + 1
        rc = p.get('reason_codes', [])
        if rc:
            reasons_list.append((tx, rc))
    print(f"Status counts: {status_counts}")
    print("Sample reasons:")
    for tx, rc in reasons_list[:10]:
        print(f"  {tx}: {rc}")
