from passlib.context import CryptContext
import psycopg2
import os

# -----------------------------
# Password hashing config
# -----------------------------
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# -----------------------------
# Database config (env-safe)
# -----------------------------
DB_NAME = os.getenv("DB_NAME", "fraudshield")
DB_USER = os.getenv("DB_USER", "vivek")
DB_PASS = os.getenv("DB_PASS", "vivek123")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5433")

# -----------------------------
# DB connection helper
# -----------------------------
def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASS,
        host=DB_HOST,
        port=DB_PORT,
    )

# -----------------------------
# Seed user data
# -----------------------------
username = "admin"
password = "admin123"   # ⚠️ demo only
role = "admin"

# bcrypt limit is 72 bytes → safe
password = password[:72]

# Hash password
hashed_password = pwd_context.hash(password)

# -----------------------------
# Insert / Update user
# -----------------------------
with get_conn() as conn:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO app_users (username, password_hash, role)
            VALUES (%s, %s, %s)
            ON CONFLICT (username)
            DO UPDATE SET
                password_hash = EXCLUDED.password_hash,
                role = EXCLUDED.role;
            """,
            (username, hashed_password, role)
        )
    conn.commit()

print("✅ Seeded user:", username)
print("🔐 Password:", password)
