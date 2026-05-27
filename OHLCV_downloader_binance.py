import requests
from datetime import timedelta, datetime
import os
import time
import csv

time_frame = input("How many days back from today do you wanna scrape(1d,2d,3d,4d...) ")


def get_time_range(date_range):
    try:
        number_of_days = int(date_range.replace("d", " "))
    except ValueError as am:
        print('Invalid Input. Please use the appropriate format "1d", "2d"')
        raise am

    endtime = datetime.now()
    startime = endtime - timedelta(days=number_of_days)

    return startime, endtime


def run_timestamp_maker(end_date) -> str:
    end_dt = datetime.fromisoformat(end_date)
    run_timestamp = end_dt.strftime("%Y-%m-%d %H:%M:%S")

    return run_timestamp


def csv_filename_maker(symbol, interval, timestamp):
    filename_str = "binance_OHLCV" + "_" + symbol + "_" + interval + "_" + timestamp

    return filename_str


def to_unix_ms(start_date, end_date):
    start_time_ms = int(start_date.timestamp() * 1000)
    end_time_ms = int(end_date.timestamp() * 1000)

    return start_time_ms, end_time_ms


def fetch_ohlcv(params_dict):
    start, end = get_time_range(time_frame)

    url = "https://api.binance.com/api/v3/klines"

    try:
        response = requests.get(url, params=params_dict)

        if response.status_code == 429:
            print("Rate limit hit. Waiting 10 seconds before retrying...")
            time.sleep(10)
        response.raise_for_status()
        data = response.json()

        # print(json.dumps(data, indent=4)) used to test the api response and see what data was returned

    except requests.exceptions.HTTPError as err:
        data = None
        print(f"HTTP error occurred: {err}")
    except requests.exceptions.JSONDecodeError:
        data = None
        print("Response was not valid JSON")
    except Exception as e:
        data = None
        print(f"An error occurred: {e}")

    return data


def csv_writer(timestamped_filename, ohlcv_data):
    folder_path = "./reports"
    file_name = timestamped_filename
    file_path = os.path.join(folder_path, file_name)
    clean_path = file_path.replace(" ", "_").replace(":", "-").replace("\\", "/")



    os.makedirs(folder_path, exist_ok=True)

    headers = ["Date", "Open", "High", "Low", "Close", "Volume"]

    with open(clean_path, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)

        for row in ohlcv_data:
            sliced_row = row[:6]

            unix_ms = sliced_row[0]
            readable_date = datetime.fromtimestamp(unix_ms / 1000).strftime("%Y-%m-%d %H:%M:%S")

            sliced_row[0] = readable_date

            writer.writerow(sliced_row)

    print(f"Successfully saved data to: {file_path}")


# ===== EXECUTION =====

start, end = get_time_range(time_frame)
csv_timestamp = run_timestamp_maker(str(end))

start_unix_ms, end_unix_ms = to_unix_ms(start, end)

params = {
    "symbol": "BTCUSDT",
    "interval": "1m",
    "startTime": start_unix_ms,
    "endTime": end_unix_ms,
    "limit": 1000,
}

# Fetch OHLCV data first
OHLCV_data = fetch_ohlcv(params)

# Then write to CSV with the data
csv_filename = csv_filename_maker(params["symbol"], params["interval"], csv_timestamp)
csv_writer(csv_filename, OHLCV_data)
