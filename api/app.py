# import os
# import json
# import time
# import select
# from typing import Optional

# import psycopg2
# from psycopg2.extras import RealDictCursor

# from fastapi import FastAPI, Query
# from fastapi.middleware.cors import CORSMiddleware
# from starlette.responses import StreamingResponse


# # ✅ DB Config (host machine connects to docker postgres via 5433)
# DB_NAME = os.getenv("DB_NAME", "fraudshield")
# DB_USER = os.getenv("DB_USER", "vivek")
# DB_PASS = os.getenv("DB_PASS", "vivek123")
# DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
# DB_PORT = os.getenv("DB_PORT", "5433")

# ALERT_TABLE = os.getenv("ALERT_TABLE", "fraud_alerts")
# NOTIFY_CHANNEL = os.getenv("NOTIFY_CHANNEL", "fraud_alerts_channel")

# app = FastAPI(title="FraudShield API", version="1.0")

# # ✅ CORS (dev)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # dev only
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


# def get_conn():
#     return psycopg2.connect(
#         dbname=DB_NAME,
#         user=DB_USER,
#         password=DB_PASS,
#         host=DB_HOST,
#         port=DB_PORT,
#     )


# @app.get("/")
# def health():
#     return {"status": "ok", "service": "FraudShield API"}


# @app.get("/alerts")
# def get_alerts(
#     limit: int = Query(50, ge=1, le=500),
#     risk_label: Optional[str] = None,
#     user_id: Optional[str] = None,
# ):
#     """
#     Fetch latest fraud alerts.
#     Filters: risk_label=HIGH/MEDIUM, user_id=user_1 etc.
#     """
#     where = []
#     params = []

#     if risk_label:
#         where.append("risk_label = %s")
#         params.append(risk_label.upper())

#     if user_id:
#         where.append("user_id = %s")
#         params.append(user_id)

#     where_sql = ("WHERE " + " AND ".join(where)) if where else ""
#     params.append(limit)

#     sql = f"""
#         SELECT alert_id, tx_id, user_id, risk_score, risk_label, reasons, created_at
#         FROM {ALERT_TABLE}
#         {where_sql}
#         ORDER BY created_at DESC
#         LIMIT %s;
#     """

#     with get_conn() as conn:
#         with conn.cursor(cursor_factory=RealDictCursor) as cur:
#             cur.execute(sql, params)
#             rows = cur.fetchall()

#     return {"count": len(rows), "alerts": rows}


# @app.get("/alerts/stats")
# def alerts_stats():
#     """
#     Quick stats for dashboard: total, high, medium
#     """
#     sql = f"""
#     SELECT
#       COUNT(*) AS total,
#       COUNT(*) FILTER (WHERE risk_label='HIGH') AS high,
#       COUNT(*) FILTER (WHERE risk_label='MEDIUM') AS medium
#     FROM {ALERT_TABLE};
#     """

#     with get_conn() as conn:
#         with conn.cursor(cursor_factory=RealDictCursor) as cur:
#             cur.execute(sql)
#             row = cur.fetchone()

#     return row


# @app.get("/alerts/count")
# def alerts_count():
#     """
#     Backward compatible endpoint (some UI calls /alerts/count)
#     """
#     sql = f"SELECT COUNT(*) AS total FROM {ALERT_TABLE};"
#     with get_conn() as conn:
#         with conn.cursor(cursor_factory=RealDictCursor) as cur:
#             cur.execute(sql)
#             row = cur.fetchone()
#     return row


# @app.get("/alerts/trend")
# def alerts_trend(minutes: int = Query(10, ge=1, le=60)):
#     """
#     Returns per-minute counts for last N minutes.
#     """
#     sql = f"""
#     WITH series AS (
#       SELECT generate_series(
#         date_trunc('minute', NOW() - (%s || ' minutes')::interval),
#         date_trunc('minute', NOW()),
#         interval '1 minute'
#       ) AS bucket
#     )
#     SELECT
#       s.bucket AS minute,
#       COALESCE(COUNT(a.*), 0) AS total,
#       COALESCE(COUNT(a.*) FILTER (WHERE a.risk_label='HIGH'), 0) AS high,
#       COALESCE(COUNT(a.*) FILTER (WHERE a.risk_label='MEDIUM'), 0) AS medium
#     FROM series s
#     LEFT JOIN {ALERT_TABLE} a
#       ON date_trunc('minute', a.created_at) = s.bucket
#     GROUP BY s.bucket
#     ORDER BY s.bucket ASC;
#     """

#     with get_conn() as conn:
#         with conn.cursor(cursor_factory=RealDictCursor) as cur:
#             cur.execute(sql, (minutes,))
#             rows = cur.fetchall()

#     return {"minutes": minutes, "points": rows}


# def sse_format(data: dict, event: str = "message") -> str:
#     return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


# @app.get("/alerts/stream")
# def alerts_stream():
#     """
#     True realtime SSE using Postgres LISTEN/NOTIFY.
#     Requires DB trigger to NOTIFY on insert.
#     """

#     def event_generator():
#         conn = None
#         try:
#             conn = get_conn()
#             conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

#             cur = conn.cursor()
#             cur.execute(f"LISTEN {NOTIFY_CHANNEL};")

#             # initial status event
#             yield sse_format({"status": "connected", "channel": NOTIFY_CHANNEL}, event="status")

#             while True:
#                 # Wait for NOTIFY up to 25s (then ping to keep alive)
#                 ready = select.select([conn], [], [], 25)
#                 if ready == ([], [], []):
#                     yield sse_format({"ts": time.time()}, event="ping")
#                     continue

#                 conn.poll()
#                 while conn.notifies:
#                     notify = conn.notifies.pop(0)
#                     payload = {}
#                     if notify.payload:
#                         try:
#                             payload = json.loads(notify.payload)
#                         except Exception:
#                             payload = {"raw": notify.payload}

#                     yield sse_format(payload, event="alert")

#         except GeneratorExit:
#             return
#         except Exception as e:
#             # Send error once
#             yield sse_format({"error": str(e)}, event="error")
#         finally:
#             try:
#                 if conn:
#                     conn.close()
#             except Exception:
#                 pass

#     headers = {
#         "Cache-Control": "no-cache",
#         "Connection": "keep-alive",
#         "X-Accel-Buffering": "no",  # for nginx (if any)
#     }

#     return StreamingResponse(
#         event_generator(),
#         media_type="text/event-stream",
#         headers=headers
#     )
import os, json, time, select, secrets, hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from fastapi import FastAPI, Query, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from starlette.responses import StreamingResponse
from passlib.context import CryptContext
from jose import jwt, JWTError
from pydantic import BaseModel

# =========================
# CONFIG
# =========================
DB_NAME = os.getenv("DB_NAME", "fraudshield")
DB_USER = os.getenv("DB_USER", "vivek")
DB_PASS = os.getenv("DB_PASS", "vivek123")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5433")

ALERT_TABLE = os.getenv("ALERT_TABLE", "fraud_alerts")
NOTIFY_CHANNEL = os.getenv("NOTIFY_CHANNEL", "fraud_alerts_channel")

JWT_SECRET = os.getenv("JWT_SECRET", "CHANGE_ME_SUPER_SECRET")  # move to .env in real
JWT_ALG = os.getenv("JWT_ALG", "HS256")
ACCESS_TTL_MIN = int(os.getenv("ACCESS_TTL_MIN", "15"))        # 15 min
REFRESH_TTL_DAYS = int(os.getenv("REFRESH_TTL_DAYS", "7"))     # 7 days

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI(title="FraudShield API", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "*"],  # dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# =========================
# REQUEST / RESPONSE MODELS
# =========================

class LoginBody(BaseModel):
    username: str
    password: str


class RefreshBody(BaseModel):
    refresh_token: str


class LogoutBody(BaseModel):
    refresh_token: str


class UserCreate(BaseModel):
    username: str
    password: str
    role: str  # "admin" or "analyst"


class UserOut(BaseModel):
    id: int
    username: str
    role: str


# =========================
# DB helper
# =========================

def get_conn():
    return psycopg2.connect(
        dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
    )

# =========================
# JWT helpers
# =========================

def now_utc():
    return datetime.now(timezone.utc)

def create_access_token(sub: str, role: str):
    exp = now_utc() + timedelta(minutes=ACCESS_TTL_MIN)
    payload = {"sub": sub, "role": role, "type": "access", "exp": exp}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG), exp

def _hash_refresh_token(token: str) -> str:
    # store only hash in DB
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def issue_refresh_token(user_id: int) -> tuple[str, datetime]:
    token = secrets.token_urlsafe(48)
    exp = now_utc() + timedelta(days=REFRESH_TTL_DAYS)
    token_hash = _hash_refresh_token(token)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO refresh_tokens (user_id, token_hash, expires_at)
                VALUES (%s, %s, %s)
                """,
                (user_id, token_hash, exp),
            )
            conn.commit()
    return token, exp

def revoke_refresh_token(token: str):
    token_hash = _hash_refresh_token(token)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE refresh_tokens SET revoked=TRUE WHERE token_hash=%s",
                (token_hash,),
            )
            conn.commit()

def rotate_refresh_token(old_token: str, user_id: int):
    # revoke old, issue new
    revoke_refresh_token(old_token)
    return issue_refresh_token(user_id)

# =========================
# Auth: DB helpers
# =========================

def get_user_by_username(username: str):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, password_hash, role FROM app_users WHERE username=%s",
                (username,),
            )
            return cur.fetchone()

def get_user_by_id(user_id: int):
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, role FROM app_users WHERE id=%s",
                (user_id,),
            )
            return cur.fetchone()

def list_all_users():
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, role FROM app_users ORDER BY id ASC"
            )
            return cur.fetchall()

def create_user(username: str, password: str, role: str):
    password_hash = pwd.hash(password)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO app_users (username, password_hash, role)
                VALUES (%s, %s, %s)
                RETURNING id, username, role
                """,
                (username, password_hash, role),
            )
            row = cur.fetchone()
            conn.commit()
            return row

def verify_password(plain: str, hashed: str) -> bool:
    return pwd.verify(plain, hashed)

# =========================
# Dependencies
# =========================

def require_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return {"username": payload["sub"], "role": payload.get("role")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid/Expired token")

def require_admin(user=Depends(require_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user

# =========================
# HEALTH
# =========================

@app.get("/")
def health():
    return {"status": "ok", "service": "FraudShield API"}

# =========================
# AUTH ROUTES
# =========================

@app.post("/auth/login")
def login(body: LoginBody):
    """
    Accepts JSON:
    { "username": "admin", "password": "admin123" }
    """
    u = get_user_by_username(body.username)
    if not u or not verify_password(body.password, u["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token, access_exp = create_access_token(u["username"], u["role"])
    refresh_token, refresh_exp = issue_refresh_token(u["id"])

    return {
        "access_token": access_token,
        "access_expires_at": access_exp.isoformat(),
        "refresh_token": refresh_token,
        "refresh_expires_at": refresh_exp.isoformat(),
        "role": u["role"],
        "username": u["username"],
    }

@app.post("/auth/refresh")
def refresh(body: RefreshBody):
    """
    Accepts JSON:
    { "refresh_token": "..." }
    """
    refresh_token = body.refresh_token
    token_hash = _hash_refresh_token(refresh_token)

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, user_id, expires_at, revoked
                FROM refresh_tokens
                WHERE token_hash=%s
                """,
                (token_hash,),
            )
            row = cur.fetchone()

    if not row or row["revoked"]:
        raise HTTPException(status_code=401, detail="Refresh token invalid")
    if row["expires_at"].replace(tzinfo=timezone.utc) < now_utc():
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = get_user_by_id(row["user_id"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # rotate refresh token
    new_refresh, new_refresh_exp = rotate_refresh_token(refresh_token, user["id"])
    access_token, access_exp = create_access_token(user["username"], user["role"])

    return {
        "access_token": access_token,
        "access_expires_at": access_exp.isoformat(),
        "refresh_token": new_refresh,
        "refresh_expires_at": new_refresh_exp.isoformat(),
        "role": user["role"],
        "username": user["username"],
    }

@app.post("/auth/logout")
def logout(body: LogoutBody):
    """
    Accepts JSON:
    { "refresh_token": "..." }
    """
    revoke_refresh_token(body.refresh_token)
    return {"ok": True}

@app.get("/auth/me")
def me(user=Depends(require_user)):
    return user

# =========================
# USER MANAGEMENT (ADMIN)
# =========================

@app.get("/users", response_model=list[UserOut])
def get_users(_=Depends(require_admin)):
    rows = list_all_users()
    return [UserOut(**row) for row in rows]

@app.post("/users", response_model=UserOut, status_code=201)
def create_user_route(body: UserCreate, _=Depends(require_admin)):
    if body.role not in ("admin", "analyst"):
        raise HTTPException(status_code=400, detail="Invalid role")
    if get_user_by_username(body.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    row = create_user(body.username, body.password, body.role)
    return UserOut(**row)

# =========================
# ALERTS (protected)
# =========================

@app.get("/alerts")
def get_alerts(
    limit: int = Query(50, ge=1, le=500),
    risk_label: Optional[str] = None,
    user_id: Optional[str] = None,
    _=Depends(require_user),
):
    where = []
    params: list = []

    if risk_label:
        where.append("risk_label = %s")
        params.append(risk_label.upper())

    if user_id:
        where.append("user_id = %s")
        params.append(user_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    params.append(limit)

    sql = f"""
        SELECT alert_id, tx_id, user_id, risk_score, risk_label, reasons, created_at
        FROM {ALERT_TABLE}
        {where_sql}
        ORDER BY created_at DESC
        LIMIT %s;
    """

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return {"count": len(rows), "alerts": rows}

@app.get("/alerts/stats")
def alerts_stats(_=Depends(require_user)):
    sql = f"""
    SELECT
      COUNT(*) AS total,
      COUNT(*) FILTER (WHERE risk_label='HIGH') AS high,
      COUNT(*) FILTER (WHERE risk_label='MEDIUM') AS medium
    FROM {ALERT_TABLE};
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql)
            row = cur.fetchone()
    return row

@app.get("/alerts/trend")
def alerts_trend(minutes: int = Query(10, ge=1, le=60), _=Depends(require_user)):
    sql = f"""
    WITH series AS (
      SELECT generate_series(
        date_trunc('minute', NOW() - (%s || ' minutes')::interval),
        date_trunc('minute', NOW()),
        interval '1 minute'
      ) AS bucket
    )
    SELECT
      s.bucket AS minute,
      COALESCE(COUNT(a.*), 0) AS total,
      COALESCE(COUNT(a.*) FILTER (WHERE a.risk_label='HIGH'), 0) AS high,
      COALESCE(COUNT(a.*) FILTER (WHERE a.risk_label='MEDIUM'), 0) AS medium
    FROM series s
    LEFT JOIN {ALERT_TABLE} a
      ON date_trunc('minute', a.created_at) = s.bucket
    GROUP BY s.bucket
    ORDER BY s.bucket ASC;
    """
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (minutes,))
            rows = cur.fetchall()
    return {"minutes": minutes, "points": rows}

# =========================
# SSE STREAM (JWT via ?token=)
# =========================

def sse_format(data: dict, event: str = "message") -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"

@app.get("/alerts/stream")
def alerts_stream(token: str = Query(..., description="JWT access token")):
    """
    SSE secured with access token as query param:
    /alerts/stream?token=...
    """
    # validate token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        if payload.get("type") != "access":
            raise Exception("bad token type")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid/Expired token")

    def event_generator():
        conn = None
        try:
            conn = get_conn()
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            cur = conn.cursor()
            cur.execute(f"LISTEN {NOTIFY_CHANNEL};")

            yield sse_format({"status": "connected", "channel": NOTIFY_CHANNEL}, event="status")

            while True:
                if select.select([conn], [], [], 30) == ([], [], []):
                    # keep-alive
                    yield sse_format({"ts": time.time()}, event="ping")
                    continue

                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    try:
                        payload = json.loads(notify.payload) if notify.payload else {}
                    except Exception:
                        payload = {"raw": notify.payload}
                    yield sse_format(payload, event="alert")

        except GeneratorExit:
            return
        except Exception as e:
            yield sse_format({"error": str(e)}, event="error")
        finally:
            try:
                if conn:
                    conn.close()
            except:
                pass

    return StreamingResponse(event_generator(), media_type="text/event-stream")
