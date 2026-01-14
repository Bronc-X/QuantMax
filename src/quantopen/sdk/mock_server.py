from fastapi import FastAPI, Depends, HTTPException, Header
from typing import Optional
import uvicorn
from datetime import datetime
import random

app = FastAPI(title="QuantMax Cloud Mock Server")

# Mock Database
VALID_API_KEYS = {"demo_key_123", "premium_user_001"}

async def verify_key(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing API Key")
    token = authorization.replace("Bearer ", "")
    if token not in VALID_API_KEYS:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return token

@app.get("/status")
def status():
    return {"status": "ok", "service": "QuantMax Cloud"}

@app.get("/v1/alpha")
def get_alpha(
    date: str, 
    universe: str = "hot_rank_top50", 
    token: str = Depends(verify_key)
):
    """
    Return mock alpha signals.
    """
    # Simulate generating signals for the requested date
    # In reality, this would query the proprietary 'quant_core' DB
    
    # Generate some random strong signals
    symbols = ["600519", "000001", "300750", "601318", "002594"]
    signals = {}
    
    # Make them vary by date string hash to be deterministic-ish
    seed = hash(date)
    random.seed(seed)
    
    for sym in symbols:
        # Score 0.0 to 1.0
        signals[sym] = round(random.random(), 4)
    
    return {
        "date": date,
        "universe": universe,
        "signals": signals  # {sym: score}
    }

def start_server():
    """Helper to run server from python"""
    uvicorn.run(app, host="127.0.0.1", port=8000)

if __name__ == "__main__":
    start_server()
