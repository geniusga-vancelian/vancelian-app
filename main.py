import os
from fastapi import FastAPI

app = FastAPI()

APP_ENV = os.getenv("APP_ENV") or os.getenv("ENV", "dev")

@app.get("/")
def root():
    return {"ok": True, "service": f"vancelian-{APP_ENV}-api"}

@app.get("/health")
def health():
    return {"status": "ok"}
