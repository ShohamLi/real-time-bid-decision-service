from fastapi import FastAPI

app = FastAPI(
    title="Real-Time Bid Decision Service",
    version="1.0.0",
    description="A simplified real-time bid decision service for an AdTech take-home assignment.",
)


@app.get("/health")
def health_check():
    return {"status": "ok"}