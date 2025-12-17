---
description: Run ALTRIOS on a BigQuery geo dataset
---

## Prerequisites
1. **Clone ALTRIOS repository**
   ```bash
   git clone https://github.com/ut-austin/altrios.git
   cd altrios
   ```
2. **Python environment** (recommended virtualenv)
   ```bash
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   pip install google-cloud-bigquery
   ```

## Step 1 – Export data from BigQuery to CSV/Parquet
```bash
# Using bq CLI (replace placeholders)
 bq extract \
   --project_id=YOUR_PROJECT \
   "YOUR_DATASET.YOUR_TABLE" \
   gs://YOUR_BUCKET/altrios_input.parquet

# Download locally
 gsutil cp gs://YOUR_BUCKET/altrios_input.parquet ./data/altrios_input.parquet
```

*Alternatively, run the Python helper script (Step 2) which performs the query and writes the file directly.*

## Step 2 – Python helper to pull and reshape data (optional)
```python
# File: scripts/export_bigquery_to_altrios.py
from google.cloud import bigquery
import pandas as pd
import os

PROJECT = "YOUR_PROJECT"
DATASET = "YOUR_DATASET"
TABLE = "YOUR_TABLE"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "altrios_input.csv")

client = bigquery.Client(project=PROJECT)
query = f"""
SELECT
  latitude,
  longitude,
  elevation_m,
  road_grade_pct,
  curve_radius_m,
  speed_kph,
  vehicle_type
FROM `{DATASET}.{TABLE}`
"""

df = client.query(query).to_dataframe()
# Ensure required columns exist – rename if needed
# df.rename(columns={"lat": "latitude", "lon": "longitude"}, inplace=True)

df.to_csv(OUTPUT_PATH, index=False)
print(f"Exported to {OUTPUT_PATH}")
```
Run it:
```bash
python scripts/export_bigquery_to_altrios.py
```

## Step 3 – Execute ALTRIOS pipeline
```bash
# From the repository root
python create_resistance_doc.py \
   --input ./data/altrios_input.csv \
   --output ./results/resistance_report.pdf
```
*If the repo provides a Streamlit UI, start it instead:*
```bash
streamlit run streamlit_app.py
```
Then upload `altrios_input.csv` via the UI.

## Step 4 – Verify output
- Open `./results/resistance_report.pdf` (or JSON/HTML) and confirm resistance values.
- Run built‑in tests (if any):
```bash
python -m altrios.tests.test_resistance --input ./data/altrios_input.csv
```

## Common Issues
| Symptom | Remedy |
|---------|--------|
| Missing column error | Add the column to your BigQuery query or rename in the pandas DataFrame before export. |
| `NaN` values | Fill with defaults (`0` for grade/curve, median speed) using `df.fillna(...)`. |
| Permission denied on GCS bucket | Grant `storage.objects.create` to the service account used by `bq`/`gsutil`. |
| Large dataset (> 1 M rows) | Use Parquet (`df.to_parquet`) and pass the Parquet file to ALTRIOS (it reads it efficiently). |

---

**End of workflow**
