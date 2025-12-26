import os
import psycopg2
from psycopg2.extras import RealDictCursor

# =========================
# Postgres config (Windows host -> Docker Postgres)
# =========================
DB_NAME = os.getenv("DB_NAME", "fraudshield")
DB_USER = os.getenv("DB_USER", "vivek")
DB_PASS = os.getenv("DB_PASS", "vivek123")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5433")  # ✅ host port because compose has 5433:5432

# Tables
RAW_TABLE = os.getenv("RAW_TABLE", "transactions_raw")
ALERT_TABLE = os.getenv("ALERT_TABLE", "fraud_alerts")


def get_pg_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
    )


def compute_risk(tx: dict):
    """
    Basic rule-based fraud scoring (0-100).
    Returns: (score:int, label:str, reasons:list[str])
    """
    score = 0
    reasons = []

    amount = float(tx.get("amount") or 0)
    channel = (tx.get("channel") or "").upper()
    is_international = bool(tx.get("is_international"))

    # Rule 1: High amount
    if amount >= 100000:
        score += 50
        reasons.append("amount>=100000")
    elif amount >= 80000:
        score += 35
        reasons.append("amount>=80000")
    elif amount >= 50000:
        score += 20
        reasons.append("amount>=50000")

    # Rule 2: International
    if is_international:
        score += 40
        reasons.append("international_transaction")

    # Rule 3: Channel risk (example rules)
    if channel == "UPI" and amount >= 50000:
        score += 20
        reasons.append("UPI_high_amount")

    if channel == "CARD" and amount >= 100000:
        score += 15
        reasons.append("CARD_very_high_amount")

    # Clamp score
    score = max(0, min(100, score))

    # Labels
    if score >= 70:
        label = "HIGH"
    elif score >= 40:
        label = "MEDIUM"
    else:
        label = "LOW"

    return score, label, reasons


def ensure_alert_table():
    sql = f"""
    CREATE TABLE IF NOT EXISTS {ALERT_TABLE} (
      alert_id BIGSERIAL PRIMARY KEY,
      tx_id TEXT NOT NULL,
      user_id TEXT,
      risk_score INT NOT NULL,
      risk_label TEXT NOT NULL,
      reasons TEXT[],
      created_at TIMESTAMP DEFAULT NOW()
    );
    """
    with get_pg_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


def detect_and_store(limit=1000):
    """
    Reads latest transactions and inserts alerts for MEDIUM/HIGH risk.
    Avoids duplicates using tx_id.
    """
    ensure_alert_table()

    with get_pg_connection() as conn:
        # 1) fetch recent rows
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # ✅ your table has tx_id, but NOT id, so order by tx_id
            cur.execute(
                f"""
                SELECT * FROM {RAW_TABLE}
                ORDER BY tx_id DESC
                LIMIT %s;
                """,
                (limit,),
            )
            rows = cur.fetchall()

        inserted = 0

        # 2) insert alerts
        with conn.cursor() as cur:
            for tx in rows:
                tx_id = tx.get("tx_id")
                user_id = tx.get("user_id")

                if not tx_id:
                    continue

                score, label, reasons = compute_risk(tx)

                # Only store MEDIUM/HIGH
                if label == "LOW":
                    continue

                # Avoid duplicates
                cur.execute(
                    f"SELECT 1 FROM {ALERT_TABLE} WHERE tx_id=%s LIMIT 1;",
                    (tx_id,),
                )
                if cur.fetchone():
                    continue

                cur.execute(
                    f"""
                    INSERT INTO {ALERT_TABLE} (tx_id, user_id, risk_score, risk_label, reasons)
                    VALUES (%s, %s, %s, %s, %s);
                    """,
                    (tx_id, user_id, score, label, reasons),
                )
                inserted += 1

        conn.commit()
        return inserted


if __name__ == "__main__":
    n = detect_and_store(limit=1000)
    print(f"✅ Inserted {n} alerts into {ALERT_TABLE}")
