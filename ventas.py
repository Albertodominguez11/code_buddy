import csv
import statistics
from datetime import datetime
from typing import Optional


def load_sales_data(filepath: str) -> list[dict]:
    """Load sales records from a CSV file."""
    records = []
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)
    return records


def parse_record(row: dict) -> Optional[dict]:
    """
    Parse and validate a raw sales record.
    Returns None if the record is invalid.
    """
    try:
        return {
            "sale_id": row["sale_id"],
            "amount": float(row["amount"]),
            "quantity": int(row["quantity"]),
            "date": datetime.strptime(row["date"], "%Y-%m-%d"),
            "region": row["region"].strip(),
            "product": row["product"].strip(),
        }
    except (KeyError, ValueError):
        return None


def compute_metrics(records: list[dict]) -> dict:
    """Compute aggregate sales metrics from parsed records."""
    if not records:
        return {}

    amounts = [r["amount"] for r in records]
    total_revenue = sum(amounts)
    avg_sale = total_revenue / len(records)

    by_region = {}
    for r in records:
        region = r["region"]
        if region not in by_region:
            by_region[region] = []
        by_region[region].append(r["amount"])

    region_totals = {region: sum(vals) for region, vals in by_region.items()}
    top_region = max(region_totals, key=region_totals.get)

    by_product = {}
    for r in records:
        product = r["product"]
        if product not in by_product:
            by_product[product] = {"revenue": 0, "units": 0}
        by_product[product]["revenue"] += r["amount"]
        by_product[product]["units"] += r["quantity"]

    return {
        "total_revenue": total_revenue,
        "average_sale": avg_sale,
        "num_transactions": len(records),
        "top_region": top_region,
        "region_totals": region_totals,
        "product_summary": by_product,
    }


def detect_anomalies(records: list[dict], threshold: float = 2.0) -> list[dict]:
    """
    Flag records where the sale amount deviates more than
    `threshold` standard deviations from the mean.
    """
    amounts = [r["amount"] for r in records]
    mean = sum(amounts) / len(amounts)
    std = statistics.stdev(amounts)

    anomalies = []
    for r in records:
        z_score = (r["amount"] - mean) / std
        if z_score > threshold:
            anomalies.append(r)

    return anomalies


def run_pipeline(filepath: str) -> dict:
    """End-to-end pipeline: load, parse, compute, detect anomalies."""
    raw = load_sales_data(filepath)

    parsed = []
    skipped = 0
    for row in raw:
        record = parse_record(row)
        if record is None:
            skipped += 1
        else:
            parsed.append(record)

    metrics = compute_metrics(parsed)
    anomalies = detect_anomalies(parsed)

    return {
        "metrics": metrics,
        "anomalies": anomalies,
        "skipped_records": skipped,
    }
