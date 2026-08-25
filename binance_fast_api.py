"""
FastAPI service that returns current price and 24h change for a symbol,
sourced live from Binance's public REST API.

Run with:
    pip install fastapi uvicorn httpx
    uvicorn binance_ticker_api:app --reload

Then hit:
    http://127.0.0.1:8000/price/BTCUSDT
    http://127.0.0.1:8000/price/ethusdt   (case-insensitive)
"""

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Binance Ticker API")

BINANCE_24HR_TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"


class TickerResponse(BaseModel):
    symbol: str
    price: float
    change_24h_percent: float
    change_24h_absolute: float
    high_24h: float
    low_24h: float
    volume_24h: float


@app.get("/price/{symbol}", response_model=TickerResponse)
async def get_price(symbol: str):
    """
    Fetch current price and 24h stats for a trading pair symbol
    (e.g. BTCUSDT, ETHUSDT, SOLUSDT). Symbol is case-insensitive.
    """
    symbol = symbol.upper()

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(BINANCE_24HR_TICKER_URL, params={"symbol": symbol})
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=502, detail=f"Could not reach Binance API: {exc}"
            )

    if resp.status_code == 400:
        # Binance returns 400 with an error payload for unknown symbols
        raise HTTPException(
            status_code=404, detail=f"Symbol '{symbol}' not found on Binance"
        )
    if resp.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Binance API returned unexpected status {resp.status_code}",
        )

    data = resp.json()

    return TickerResponse(
        symbol=data["symbol"],
        price=float(data["lastPrice"]),
        change_24h_percent=float(data["priceChangePercent"]),
        change_24h_absolute=float(data["priceChange"]),
        high_24h=float(data["highPrice"]),
        low_24h=float(data["lowPrice"]),
        volume_24h=float(data["volume"]),
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
