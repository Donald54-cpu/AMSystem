from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import asyncpg
import os
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Autoriser les requêtes CORS pour le développement
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration PostgreSQL (utilisez les infos de Supabase)
DATABASE_URL = os.getenv("https://mraibixatihdjybdmdkq.supabase.co", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im1yYWliaXhhdGloZGp5YmRtZGtxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQwNDA0OTIsImV4cCI6MjA1OTYxNjQ5Mn0.RIZVG0jlljeYPl5U_o3DmsM0qSfFMiMcC1eewGU0My4")

class MotorData(BaseModel):
    motor_id: int
    temperature: float
    voltage: float
    timestamp: datetime = None

class ThresholdData(BaseModel):
    motor_id: int
    temp_max: float
    voltage_min: float
    voltage_max: float

async def get_db():
    return await asyncpg.connect(DATABASE_URL)

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

@app.get("/api/data/{motor_id}/history")
async def get_motor_history(motor_id: int, limit: int = 100):
    conn = await get_db()
    try:
        records = await conn.fetch(
            "SELECT * FROM thermocouple_data WHERE motor_id = $1 ORDER BY timestamp DESC LIMIT $2",
            motor_id, limit
        )
        return [dict(record) for record in records]
    finally:
        await conn.close()

@app.get("/api/thresholds/{motor_id}")
async def get_thresholds(motor_id: int):
    conn = await get_db()
    try:
        thresholds = await conn.fetchrow(
            "SELECT * FROM thresholds WHERE motor_id = $1", motor_id)
        if not thresholds:
            raise HTTPException(status_code=404, detail="Thresholds not found")
        return dict(thresholds)
    finally:
        await conn.close()

@app.post("/api/thresholds/")
async def update_thresholds(data: ThresholdData):
    conn = await get_db()
    try:
        await conn.execute("""
        INSERT INTO thresholds (motor_id, temp_max, voltage_min, voltage_max)
        VALUES ($1, $2, $3, $4)
        ON CONFLICT (motor_id) DO UPDATE SET
            temp_max = EXCLUDED.temp_max,
            voltage_min = EXCLUDED.voltage_min,
            voltage_max = EXCLUDED.voltage_max
        """, data.motor_id, data.temp_max, data.voltage_min, data.voltage_max)
        return {"status": "success"}
    finally:
        await conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)