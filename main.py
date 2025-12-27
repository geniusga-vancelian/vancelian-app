from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def root():
    return {"ok": True, "service": "vancelian-dev-api"}
@app.get("/health")
def health():
    return {"status": "ok"}
