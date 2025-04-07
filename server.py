from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import asyncpg  # Remplace sqlite3
import uvicorn
import asyncio
import random
import time
import os
from dotenv import load_dotenv

load_dotenv()  # Pour les variables d'environnement

app = FastAPI()

# Configuration PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/thermocouple")

async def get_db():
    return await asyncpg.connect(DATABASE_URL)

async def init_db():
    conn = await get_db()
    try:
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS thermocouple_data (
            id SERIAL PRIMARY KEY,
            motor_id INTEGER,
            temperature REAL,
            voltage REAL,
            timestamp TIMESTAMP
        )
        """)
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS thresholds (
            motor_id INTEGER PRIMARY KEY,
            temp_max REAL,
            voltage_min REAL,
            voltage_max REAL
        )
        """)
    finally:
        await conn.close()

# Modifiez toutes les fonctions pour utiliser async/await avec asyncpg
# Exemple pour receive_motor_data:
@app.post("/api/data/")
async def receive_motor_data(data: MotorData):
    conn = await get_db()
    try:
        await conn.execute("""
        INSERT INTO thermocouple_data (motor_id, temperature, voltage, timestamp)
        VALUES ($1, $2, $3, $4)
        """, data.motor_id, data.temperature, data.voltage, data.timestamp or datetime.now())
        
        # Vérification des seuils
        thresholds = await conn.fetchrow(
            "SELECT * FROM thresholds WHERE motor_id = $1", data.motor_id)
        
        alerts = []
        if thresholds:
            if data.temperature > thresholds['temp_max']:
                alerts.append({"motor_id": data.motor_id, "alert_type": "HIGH_TEMP"})
            if data.voltage < thresholds['voltage_min'] or data.voltage > thresholds['voltage_max']:
                alerts.append({"motor_id": data.motor_id, "alert_type": "VOLTAGE_ANOMALY"})
        
        return {"status": "success", "alerts": alerts}
    finally:
        await conn.close()

# ... (adaptez toutes les autres fonctions de la même manière)