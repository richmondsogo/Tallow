import multiprocessing
import warnings

import pandas as pd
import backtesting
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

# Suppress noisy margin-cancellation warnings
warnings.filterwarnings("ignore", category=UserWarning, module="backtesting")

# 1 traded "unit" = 1e-5 BTC (roughly $1 at $100k/BTC), giving fine
# fractional-like granularity while keeping every unit a whole number,
# which avoids the FractionalBacktest + multiprocessing bug entirely.
UNIT_SCALE = 1e-5


# --- TECHNICAL INDICATORS ---
def SMA(values, n):
    return pd.Series(values).rolling(n).mean()


def EMA(values, n):
    return pd.Series(values).ewm(span=n, adjust=False).mean()


def ATR(high, low, close, n=14):
    """Calculates Average True Range for smart stop losses"""
    h = pd.Series(high)
    l = pd.Series(low)
    c = pd.Series(close)
    tr1 = h - l
    tr2 = (h - c.shift()).abs()
    tr3 = (l - c.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(n).mean()


# --- THE TWO-WAY STRATEGY ---
class TrendFilterCrossover(Strategy):
    ema_fast_period = 24
    ema_slow_period = 52
    sma_filter_period = 200
    atr_period = 14
    atr_multiplier = 3.0  # Dynamic distance for stop loss

    def init(self):
        price = self.data.Close
        self.ema12 = self.I(EMA, price, self.ema_fast_period)
        self.ema26 = self.I(EMA, price, self.ema_slow_period)
        self.sma50 = self.I(SMA, price, self.sma_filter_period)
        self.atr = self.I(ATR, self.data.High, self.data.Low, price, self.atr_period)

    def next(self):
        current_price = self.data.Close[-1]
        current_sma50 = self.sma50[-1]
        current_atr = self.atr[-1]

        # 1. MANAGEMENT FOR EXISTING POSITIONS
        if self.position:
            if self.position.is_long and current_price < current_sma50:
                self.position.close()
            elif self.position.is_short and current_price > current_sma50:
                self.position.close()
            return

        # 2. ENTRY LOGIC (Executes only when flat)
        if current_price > current_sma50:
            if crossover(self.ema12, self.ema26):  # type: ignore
                sl_price = current_price - (self.atr_multiplier * current_atr)
                self.buy(sl=sl_price, size=0.95)

        elif current_price < current_sma50:
            if crossover(self.ema26, self.ema12):  # type: ignore
                sl_price = current_price + (self.atr_multiplier * current_atr)
                self.sell(sl=sl_price, size=0.95)


def main():
    # --- LOAD CUSTOM CSV DATA ---
    df = pd.read_csv(
        r"C:\Users\Richmond\Desktop\Codebase\Tallow\reports\OHLCV_data\binance_OHLCV_BTCUSDT_1h_2026-06-09_01-39-26.csv"
    )
    df.columns = df.columns.str.strip().str.lower()
    df = df.rename(
        columns={
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)
    df = df.sort_index()

    # Rescale OHLC into small tradeable "units" so whole-number position
    # sizing gives fine granularity without needing FractionalBacktest.
    # (This does NOT change your $ P&L, cash, or returns — only the
    # internal price-per-unit used for order sizing.)
    for col in ("Open", "High", "Low", "Close"):
        df[col] = df[col] * UNIT_SCALE

    # --- RUN ENGINE ---
    bt = Backtest(
        df,
        TrendFilterCrossover,
        cash=100_000,
        commission=0.001,  # 0.1% binance spot default fee
        exclusive_orders=True,
        finalize_trades=True,
    )

    stats, heatmap = bt.optimize(  # type: ignore
        ema_fast_period=range(10, 40, 5),
        ema_slow_period=range(40, 80, 5),
        atr_multiplier=[2.0, 2.5, 3.0, 3.5, 4.0],
        maximize="Sharpe Ratio",
        constraint=lambda p: p.ema_fast_period < p.ema_slow_period,  # type: ignore
        return_heatmap=True,
    )

    print(stats)
    print("\n--- BEST PARAMETERS FOUND ---")
    print(stats._strategy)

    print("# Trades:", stats["# Trades"])
    print("Return [%]:", stats["Return [%]"])
    print("Sharpe Ratio:", stats["Sharpe Ratio"])
    print("Sortino Ratio:", stats["Sortino Ratio"])


if __name__ == "__main__":
    multiprocessing.freeze_support()
    backtesting.Pool = multiprocessing.Pool
    main()

    # ── OPTIMIZATION METRIC NOTES ────────────────────────────────────────────
    # maximize="Sharpe Ratio" ranks parameter combos by return-per-unit-of-risk,
    # not just raw profit. Formula: (avg return) / (std dev of returns).
    # A high Sharpe means the equity curve grew steadily, not that it grew big.
    #
    # Caveats to keep in mind when reading the "best" params below:
    #   1. Sharpe penalizes ALL volatility, including big winning spikes —
    #      it can't tell "good" swings from "bad" swings. Sortino Ratio
    #      (stats["Sortino Ratio"]) only penalizes downside moves if that's
    #      closer to what you actually care about.
    #   2. Sharpe says nothing about drawdown depth/duration. Always check
    #      stats["Max. Drawdown [%]"] alongside it — a strategy can have a
    #      solid Sharpe and still have one brutal 40%+ drawdown mid-run.
    #   3. Low trade count (stats["# Trades"]) makes Sharpe noisy/unreliable —
    #      it's computed from a return distribution, so too few trades can
    #      produce NaN or misleadingly extreme values.
    #   4. A high in-sample Sharpe on a narrow grid (240 combos here) is a
    #      classic overfitting trap — the "best" combo may just fit this
    #      dataset's noise rather than reflect genuine, repeatable edge.
    #      Validate on out-of-sample / walk-forward data before trusting it.
    #
    # Rule of thumb: don't optimize on Sharpe alone — cross-check
    # # Trades, Max Drawdown, and (ideally) out-of-sample performance
    # before treating the "best" params as real.
    # ──────────────────────────────────────────────────────────────────────
