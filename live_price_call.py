import json
import threading
import time
import websocket

# Global variable to store the latest price
current_price = None
price_lock = threading.Lock()


def on_message(ws, message):
    global current_price
    data = json.loads(message)
    with price_lock:
        current_price = float(data["c"])


def on_error(ws, error):
    print(f"WebSocket error: {error}")


def on_close(ws, close_status_code, close_msg):
    print("WebSocket closed")


def on_open(ws):
    # Subscribe to the real-time price updates for the given symbol
    symbol = "btcusdt"
    ws.send(
        json.dumps({"method": "SUBSCRIBE", "params": [f"{symbol}@ticker"], "id": 1})
    )


def print_price_periodically():
    """Print the current price every 5 seconds"""
    while True:
        time.sleep(5)
        with price_lock:
            if current_price is not None:
                print(f"Current BTC/USDT Price: ${current_price}")


if __name__ == "__main__":
    # Start the price printing thread as a daemon
    print_thread = threading.Thread(target=print_price_periodically, daemon=True)
    print_thread.start()

    # Start the WebSocket connection
    websocket.enableTrace(False)
    ws = websocket.WebSocketApp(
        "wss://stream.binance.com:9443/ws",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.on_open = on_open
    ws.run_forever()
