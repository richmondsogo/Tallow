import requests
from datetime import timedelta, datetime
import os
import time
import csv

time_frame = input(
    "How many days back from today do you wanna scrape(1d,2d,3d,4d...): "
)


def get_time_range(date_range):
    try:
        # Fixed the string replacement so it safely casts to int
        number_of_days = int(date_range.replace("d", "").strip())
    except ValueError as am:
        print('Invalid Input. Please use the appropriate format "1d", "2d"')
        raise am

    endtime = datetime.now()
    startime = endtime - timedelta(days=number_of_days)

    return startime, endtime


def run_timestamp_maker(end_date) -> str:
    end_dt = datetime.fromisoformat(end_date)
    run_timestamp = end_dt.strftime("%Y-%m-%d_%H-%M-%S")
    return run_timestamp


def csv_filename_maker(symbol, interval, timestamp):
    # Added the .csv extension here directly!
    filename_str = f"binance_OHLCV_{symbol}_{interval}_{timestamp}.csv"
    return filename_str


def to_unix_ms(start_date, end_date):
    start_time_ms = int(start_date.timestamp() * 1000)
    end_time_ms = int(end_date.timestamp() * 1000)
    return start_time_ms, end_time_ms


def fetch_with_retry(url, params_dict, max_retries=5, backoff_factor=10):
    """Robust HTTP GET request with retries and exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params_dict)

            # If we hit the rate limit, we sleep and retry
            if response.status_code == 429:
                print(
                    f"Rate limit hit. Waiting {backoff_factor} seconds before retrying..."
                )
                time.sleep(backoff_factor)
                backoff_factor *= 2  # Exponential backoff (10s, 20s, 40s...)
                continue

            response.raise_for_status()
            return response.json()

        except requests.exceptions.HTTPError as err:
            print(f"HTTP error occurred: {err}")
            return None
        except requests.exceptions.JSONDecodeError:
            print("Response was not valid JSON")
            return None
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    print("Max retries exceeded. Aborting this request.")
    return None


def fetch_ohlcv(symbol, interval, start_ms, end_ms):
    """Paginates Binance API to fetch massive datasets beyond the 1000 row limit."""
    url = "https://api.binance.com/api/v3/klines"
    all_klines = []
    current_start = start_ms
    limit = 1000  # Binance's maximum rows per request

    print(
        f"Fetching data from {datetime.fromtimestamp(start_ms/1000)} to {datetime.fromtimestamp(end_ms/1000)}"
    )

    # Loop until our start time catches up with our requested end time
    while current_start < end_ms:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": current_start,
            "endTime": end_ms,
            "limit": limit,
        }

        # Send the API call using our robust retry function
        data = fetch_with_retry(url, params)

        if not data:
            print("Data fetch failed or stopped. Exiting pagination loop.")
            break

        all_klines.extend(data)
        print(f"Fetched {len(data)} rows... Total accumulated: {len(all_klines)}")

        # If we get back less than our limit, we have successfully scraped all available data!
        if len(data) < limit:
            break

        # Update our next request's start time to the closeTime of the final candle in the batch (+ 1 ms to prevent duplicates)
        current_start = data[-1][6] + 1

        # A tiny delay just to be polite to Binance's servers
        time.sleep(0.1)

    return all_klines


def csv_writer(timestamped_filename, ohlcv_data):
    if not ohlcv_data:
        print("No data received. CSV was not created.")
        return

    folder_path = "./reports/OHLCV_data"
    file_path = os.path.join(folder_path, timestamped_filename)

    # Strip spaces and colons so file paths don't freak out on Windows OS
    clean_path = file_path.replace(" ", "_").replace(":", "-").replace("\\", "/")

    os.makedirs(folder_path, exist_ok=True)

    headers = ["Date", "Open", "High", "Low", "Close", "Volume"]

    with open(clean_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for row in ohlcv_data:
            sliced_row = row[:6]

            # Format UNIX timestamp to Human Readable
            unix_ms = sliced_row[0]
            readable_date = datetime.fromtimestamp(unix_ms / 1000).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
            sliced_row[0] = readable_date

            writer.writerow(sliced_row)

    print(f"Successfully saved {len(ohlcv_data)} rows of data to: {clean_path}")


# ===== EXECUTION =====
try:
    start, end = get_time_range(time_frame)
    csv_timestamp = run_timestamp_maker(str(end))

    start_unix_ms, end_unix_ms = to_unix_ms(start, end)

    symbol = "BTCUSDT"
    interval = "1m"

    # 1. Fetch paginated OHLCV data first
    OHLCV_data = fetch_ohlcv(symbol, interval, start_unix_ms, end_unix_ms)

    # 2. Construct the file name and trigger the save
    csv_filename = csv_filename_maker(symbol, interval, csv_timestamp)
    csv_writer(csv_filename, OHLCV_data)

except Exception as e:
    print(f"Script execution failed: {e}")
