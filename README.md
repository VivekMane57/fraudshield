# FraudShield – Realtime Fraud Detection Dashboard

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
