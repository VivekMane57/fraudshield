import json
import time
from datetime import datetime

from kafka import KafkaConsumer
import psycopg2
from psycopg2.extras import Json


DB_NAME = "fraudshield"
DB_USER = "vivek"
DB_PASS = "vivek123"
DB_HOST = "127.0.0.1"   # be explicit
DB_PORT = "5433"        # 👈 use new host port



# --------------------------
# Kafka configuration
# --------------------------
KAFKA_BROKER = "localhost:9092"
KAFKA_TOPIC = "transactions_raw"


def get_pg_connection():
    """
    Open a PostgreSQL connection.
    """
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
    )


def ensure_table_exists():
    """
    Create transactions_raw table if it does not exist.
    """
    create_sql = """
    CREATE TABLE IF NOT EXISTS transactions_raw (
        tx_id            VARCHAR(64) PRIMARY KEY,
        user_id          VARCHAR(64),
        account_id       VARCHAR(64),
        merchant_id      VARCHAR(64),
        amount           NUMERIC(12,2),
        currency         VARCHAR(10),
        channel          VARCHAR(32),
        device_id        VARCHAR(64),
        ip_address       VARCHAR(45),
        geo_city         VARCHAR(64),
        geo_country      VARCHAR(4),
        is_international BOOLEAN,
        event_time_utc   TIMESTAMPTZ,
        is_fraud_label   INT,
        raw_payload      JSONB,
        kafka_partition  INT,
        kafka_offset     BIGINT,
        inserted_at      TIMESTAMPTZ DEFAULT NOW()
    );
    """

    conn = get_pg_connection()
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute(create_sql)
    conn.close()


def save_to_db(conn, data: dict, partition: int, offset: int):
    """
    Insert one transaction into Postgres.
    """
    sql = """
    INSERT INTO transactions_raw (
        tx_id,
        user_id,
        account_id,
        merchant_id,
        amount,
        currency,
        channel,
        device_id,
        ip_address,
        geo_city,
        geo_country,
        is_international,
        event_time_utc,
        is_fraud_label,
        raw_payload,
        kafka_partition,
        kafka_offset
    )
    VALUES (
        %(tx_id)s,
        %(user_id)s,
        %(account_id)s,
        %(merchant_id)s,
        %(amount)s,
        %(currency)s,
        %(channel)s,
        %(device_id)s,
        %(ip_address)s,
        %(geo_city)s,
        %(geo_country)s,
        %(is_international)s,
        %(event_time_utc)s,
        %(is_fraud_label)s,
        %(raw_payload)s,
        %(kafka_partition)s,
        %(kafka_offset)s
    )
    ON CONFLICT (tx_id) DO NOTHING;
    """

    payload = {
        "tx_id": data.get("tx_id"),
        "user_id": data.get("user_id"),
        "account_id": data.get("account_id"),
        "merchant_id": data.get("merchant_id"),
        "amount": data.get("amount"),
        "currency": data.get("currency"),
        "channel": data.get("channel"),
        "device_id": data.get("device_id"),
        "ip_address": data.get("ip_address"),
        "geo_city": data.get("geo_city"),
        "geo_country": data.get("geo_country"),
        "is_international": data.get("is_international"),
        "event_time_utc": data.get("timestamp"),
        "is_fraud_label": data.get("is_fraud_label", 0),
        "raw_payload": Json(data),
        "kafka_partition": partition,
        "kafka_offset": offset,
    }

    with conn.cursor() as cur:
        cur.execute(sql, payload)


def start_consumer():
    """
    Start Kafka consumer and stream data into Postgres.
    """
    # 1. ensure table exists
    ensure_table_exists()

    # 2. connect to DB once and reuse connection
    conn = get_pg_connection()
    conn.autocommit = True

    # 3. configure Kafka consumer
    consumer = KafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=[KAFKA_BROKER],
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="fraudshield-consumer",
    )

    print("🚀 Kafka → Postgres consumer started. Listening for messages...")

    try:
        for msg in consumer:
            data = msg.value
            print(f"📥 Received from Kafka (partition={msg.partition}, offset={msg.offset}): {data}")

            try:
                save_to_db(conn, data, msg.partition, msg.offset)
                print("✅ Saved to Postgres.")
            except Exception as e:
                print(f"❌ Error saving to DB: {e}")
                # optionally reconnect if connection broke
                try:
                    conn.close()
                except Exception:
                    pass
                time.sleep(2)
                conn = get_pg_connection()
                conn.autocommit = True

    except KeyboardInterrupt:
        print("🛑 Stopping consumer...")
    finally:
        try:
            consumer.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    start_consumer()
