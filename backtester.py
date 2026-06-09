import pandas as pd
from backtesting import Backtest, Strategy
from backtesting.lib import crossover

# --- 1. LOAD YOUR CUSTOM CSV DATA ---
df = pd.read_csv(
    "C:\\Users\\Richmond\\Desktop\\Codebase\\Tallow\\reports\\OHLCV_data\\binance_OHLCV_BTCUSDT_1h_2026-06-09_01-39-26.csv"
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


# --- 2. TECHNICAL INDICATORS ---
def SMA(values, n):
    return pd.Series(values).rolling(n).mean()


def EMA(values, n):
    return pd.Series(values).ewm(span=n, adjust=False).mean()


def ATR(high, low, close, n=14):
    """Calculates Average True Range for smart stop losses"""
    h = pd.Series(high)
    l = pd.Series(low)  # noqa: E741
    c = pd.Series(close)
    tr1 = h - l
    tr2 = (h - c.shift()).abs()
    tr3 = (l - c.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(n).mean()


# --- 3. THE TWO-WAY STRATEGY ---
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
                self.buy(sl=sl_price)

        elif current_price < current_sma50:
            if crossover(self.ema26, self.ema12):  # type: ignore
                sl_price = current_price + (self.atr_multiplier * current_atr)
                self.sell(sl=sl_price)


# --- 4. RUN THE ENGINE ---
bt = Backtest(
    df,
    TrendFilterCrossover,
    cash=100_000_000,
    commission=0.0001,  # 0.01% fee VIP tier
    exclusive_orders=True,
    finalize_trades=True,
)


stats, heatmap = bt.optimize(  # type: ignore
    ema_fast_period=range(10, 40, 5),
    ema_slow_period=range(40, 80, 5),
    atr_multiplier=[2.0, 2.5, 3.0, 3.5, 4.0],
    maximize="Equity Final [$]",
    constraint=lambda p: p.ema_fast_period < p.ema_slow_period,  # type: ignore
    return_heatmap=True,
)

print(stats)
print("\n--- BEST PARAMETERS FOUND ---")
# print(stats._strategy)

