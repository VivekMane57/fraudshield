import json
import random
import time
from datetime import datetime
from kafka import KafkaProducer

TOPIC = "transactions_raw"

producer = KafkaProducer(
    bootstrap_servers="localhost:9092",
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
)

USERS = [f"user_{i}" for i in range(1, 6)]
MERCHANTS = ["amazon", "flipkart", "myntra", "swiggy", "zomato"]
CHANNELS = ["UPI", "CARD", "NETBANKING"]


def generate_transaction():
    amount = round(random.uniform(50, 150000), 2)
    return {
        "tx_id": f"tx_{int(time.time() * 1000)}",
        "user_id": random.choice(USERS),
        "account_id": f"acct_{random.randint(1, 3)}",
        "merchant_id": random.choice(MERCHANTS),
        "amount": amount,
        "currency": "INR",
        "channel": random.choice(CHANNELS),
        "device_id": f"dev_{random.randint(1, 4)}",
        "ip_address": f"192.168.1.{random.randint(2, 254)}",
        "geo_city": random.choice(["Kolhapur", "Pune", "Mumbai", "Delhi"]),
        "geo_country": "IN",
        "is_international": False,
        "timestamp": datetime.utcnow().isoformat(),
    }


if __name__ == "__main__":
    print("Starting transaction producer…")
    try:
        while True:
            tx = generate_transaction()
            producer.send(TOPIC, tx)
            print("Sent:", tx)
            time.sleep(1)
    except KeyboardInterrupt:
        print("Producer stopped.")
