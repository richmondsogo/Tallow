import matplotlib.pyplot as plt
import pandas as pd


# 1. Load data and explicitly parse the Date column
file_path = r"C:\Users\Richmond\Desktop\Codebase\Tallow\reports\trend_following_indicators\binance_OHLCV_BTCUSDT_1m_2026-05-30_14-21-02_with_indicators.csv"
df = pd.read_csv(file_path)

# Ensure 'Date' is handled as actual timestamps and set it as the index
df["Date"] = pd.to_datetime(df["Date"])
df.set_index("Date", inplace=True)

# 2. Apply a modern dark theme style block
plt.style.use("dark_background")
fig, ax = plt.subplots(figsize=(14, 7), facecolor="#121212")
ax.set_facecolor("#1e1e1e")

# 3. Plot with deliberate visual hierarchy (varying weights and transparency)
ax.plot(
    df.index, df["Close"], label="BTC Close", color="#FFFFFF", linewidth=2.0, alpha=0.9
)

# Short-term Momentum (EMAs) - Thinner, slightly transparent lines
ax.plot(
    df.index,
    df["EMA_12"],
    label="EMA 12 (Short)",
    color="#26a69a",
    linewidth=1.0,
    alpha=0.8,
    linestyle="--",
)
ax.plot(
    df.index,
    df["EMA_26"],
    label="EMA 26 (Mid)",
    color="#ef5350",
    linewidth=1.0,
    alpha=0.8,
    linestyle="--",
)

# Long-term Trend (SMAs) - Solid, distinct colors
ax.plot(
    df.index, df["SMA_20"], label="SMA 20", color="#ffb74d", linewidth=1.5, alpha=0.8
)
ax.plot(
    df.index,
    df["SMA_50"],
    label="SMA 50 (Baseline)",
    color="#2196f3",
    linewidth=1.5,
    alpha=0.8,
)

# 4. Refine titles, typography, and layout formatting
ax.set_title(
    "BTCUSDT 1m — Price Action & Moving Averages",
    fontsize=14,
    fontweight="bold",
    pad=15,
    color="#E0E0E0",
)
ax.set_xlabel("Time", fontsize=11, color="#A0A0A0")
ax.set_ylabel("Price (USDT)", fontsize=11, color="#A0A0A0")

# Format chart grids to be subtle background indicators rather than harsh lines
ax.grid(True, linestyle="--", alpha=0.15, color="#FFFFFF")

# Clean up layout variables and position the legend safely outside or clear of charts
ax.legend(
    loc="upper left",
    frameon=True,
    facecolor="#1e1e1e",
    edgecolor="#333333",
    fontsize=10,
)

# Beautifully tilt the date labels automatically so they don't smash into each other
fig.autofmt_xdate()

plt.tight_layout()
plt.show()
