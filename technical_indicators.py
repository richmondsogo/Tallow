from pathlib import Path
import pandas as pd

file_path = Path("./reports/OHLCV_data/binance_OHLCV_BTCUSDT_1m_2026-05-30_14-21-02.csv")

df = pd.read_csv(file_path)

df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date").reset_index(drop=True)

df["SMA_20"] = df["Close"].rolling(window=20).mean()
df["SMA_50"] = df["Close"].rolling(window=50).mean()


df["EMA_12"] = df["Close"].ewm(span=12, adjust=False).mean()
df["EMA_26"] = df["Close"].ewm(span=26, adjust=False).mean()


new_filename = f"{file_path.stem}_with_indicators{file_path.suffix}"
parent_dir = file_path.parent.parent


new_path = parent_dir / "trend_following_indicators" / new_filename
new_path.parent.mkdir(parents=True, exist_ok=True)

if new_path.suffix != ".csv":
    new_path = new_path.with_suffix(".csv")

df.to_csv(new_path, index=False)
print(f"Technical indicators added and saved to: {new_path}")
