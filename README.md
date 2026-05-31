# FraudShield – Realtime Fraud Detection Dashboard
![Python](https://img.shields.io/badge/Python-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-20232A?style=flat&logo=react&logoColor=61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white)
![Kafka](https://img.shields.io/badge/Kafka-231F20?style=flat&logo=apachekafka&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?style=flat&logo=typescript&logoColor=white)

Realtime fraud alerts on top of **PostgreSQL + FastAPI + Kafka + SSE + React (Vite)**  
Role-based login (admin / analyst) + User management + Live alert stream.

## 🚀 Features

- 🔐 JWT-based authentication (access + refresh tokens)
- 👥 Role-based access (admin / analyst)
- 📊 Realtime dashboard (KPI cards, risk distribution pie, last 10 min trend)
- 📡 Server-Sent Events (SSE) based streaming from PostgreSQL NOTIFY
- 📁 CSV export for alerts
- 👨‍💼 User management (admin creates new users)

## 🧱 Tech Stack

**Backend**
- FastAPI
- PostgreSQL
- psycopg2
- passlib (bcrypt)
- jose (JWT)

**Frontend**
- React + TypeScript + Vite
- Tailwind CSS
- Recharts
- lucide-react icons

## 🗂 Project Structure

```bash
fraudshield/
  api/
    app.py               # FastAPI app (auth + alerts + SSE + user mgmt)
    seed_user.py         # Script to create initial admin user
  generator/
    transaction_producer.py  # Kafka / dummy tx generator
  processor/
    fraud_detector.py        # Consumes tx, writes fraud_alerts
    kafka_to_postgres.py     # Push to PostgreSQL
  frontend/
    src/
      App.tsx                # Dashboard + login + user management
      assets/api.ts          # API helper & auth storage

⚙️ Backend – Local Setup
cd fraudshield
python -m venv venv
venv\Scripts\activate  # Windows

pip install -r requirements.txt

# Set environment (example)
set DB_NAME=fraudshield
set DB_USER=vivek
set DB_PASS=vivek123
set DB_HOST=127.0.0.1
set DB_PORT=5433
set JWT_SECRET=super_secret_change_me

# run migrations / create tables manually (describe shortly here)

uvicorn api.app:app --reload --host 127.0.0.1 --port 8000

⚙️ Backend Setup (Local Dev)

cd fraudshield
python -m venv venv
venv\Scripts\activate         # Windows
pip install -r requirements.txt

cd fraudshield
python -m venv venv
venv\Scripts\activate         # Windows
pip install -r requirements.txt

PostgreSQL setup
CREATE DATABASE fraudshield;
\c fraudshield;

CREATE TABLE app_users (
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT DEFAULT 'analyst'
);

CREATE TABLE refresh_tokens (
  id SERIAL PRIMARY KEY,
  user_id INT REFERENCES app_users(id),
  token_hash TEXT NOT NULL,
  expires_at TIMESTAMP NOT NULL,
  revoked BOOLEAN DEFAULT FALSE
);

CREATE TABLE fraud_alerts (
  alert_id SERIAL PRIMARY KEY,
  tx_id TEXT,
  user_id TEXT,
  risk_score FLOAT,
  risk_label TEXT,
  reasons TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

Seed initial admin user
python api/seed_user.py


Admin credentials:

username: admin
password: admin123

Start backend
uvicorn api.app:app --reload --host 127.0.0.1 --port 8000

💻 Frontend Setup
cd frontend
npm install
npm run dev


📍 Opens at:
➡️ http://localhost:5173

Add .env:

VITE_API_BASE=http://127.0.0.1:8000

🔐 Auth Endpoints (Summary)
Endpoint	Method	Description
/auth/login	POST	Get access + refresh token
/auth/refresh	POST	Rotate refresh token
/auth/logout	POST	Invalidate refresh token
/auth/me	GET	Verify logged-in user
/alerts	GET	Fraud alerts list
/alerts/stream	GET	SSE realtime stream
/users	GET/POST	Admin only (manage users)
🎯 How to Demo

1️⃣ Login as admin
2️⃣ Watch live dashboard updates
3️⃣ Create new analyst user
4️⃣ Try login as analyst → fewer permissions
5️⃣ Run Kafka + fraud detector for continuous live alerts

🧭 Future Enhancements

Pagination + advanced filters

Detailed alert drill-down UI

Real ML model integration

Deployment on Render / Railway / AWS
