from time import sleep
from requests import get, exceptions
from glom import Coalesce, glom
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table


def retry_with_retry(url):

    try:
        response = get(url)
        if response.status_code == 429:
            print("Rate limit hit. Waiting 10 seconds before retrying...")
            sleep(10)
            response = get(url)  # Retry once

        response.raise_for_status()
        return response.json()
    except exceptions.HTTPError as err:
        print(f"HTTP error occurred: {err}")
    except exceptions.JSONDecodeError:
        print("Response was not valid JSON")
    except Exception as e:
        print(f"An error occurred: {e}")
    return None


def fetch_active_tokens():
    url = "https://api.dexscreener.com/token-profiles/latest/v1"
    return retry_with_retry(url)


def tokens_parser(token_metadata):
    if not token_metadata:
        return []

    token_address = [
        item["tokenAddress"] for item in token_metadata if "tokenAddress" in item
    ]

    # remove duplicates from token_address
    return list(dict.fromkeys(token_address))


def multi_token_url_builder(tokens_address_list):
    return ",".join(tokens_address_list)


def bulk_metric_retrieval(token_string):
    all_pairs = []  # Changed name for clarity

    chunk_size = 15

    batches = [
        token_string[i : i + chunk_size]
        for i in range(0, len(token_string), chunk_size)
    ]

    for batch in batches:
        payload = ",".join(batch)
        url = f"https://api.dexscreener.com/latest/dex/tokens/{payload}"
        data = retry_with_retry(url)
        if data and "pairs" in data and data["pairs"]:
            all_pairs.extend(data["pairs"])

    # pprint(all_pairs, indent=3)
    return all_pairs


def minimalist_metric_parser(all_token_list):
    sorted_pools = sorted(all_token_list, key=lambda x: x.get("liquidity", {}).get("usd", 0), reverse=True)
    seen_addresses = set()
    highest_liquidity_pools = []
    
    for pool in sorted_pools:
        token_address = pool.get("baseToken", {}).get("address")
        if token_address and token_address not in seen_addresses:
            highest_liquidity_pools.append(pool)
            seen_addresses.add(token_address)

    blueprint = [
        {
            "Token Name": Coalesce("baseToken.name", default="Unknown"),
            "Contract Address": Coalesce("baseToken.address", default="N/A"),
            "Chain": Coalesce("chainId", default="N/A"),
            "Dex": Coalesce("dexId", default="N/A"),
            "Market Cap": Coalesce("marketCap", default=0),
            "Pair Age": Coalesce("pairCreatedAt", default=None),
            "24h Volume": Coalesce("volume.h24", default=0),
            "Liquidity": Coalesce("liquidity.usd", default=0),
        }
    ]

    extracted_data = glom(highest_liquidity_pools, blueprint)
    return extracted_data


# Identity: baseToken.address, baseToken.name, baseToken.symbol, and chainIdMetrics: marketCap and volume.h24Time: pairCreatedAt
# Token Name | Chain | Market Cap | 24h Volume | Age. ohh so i wanna add liquidity to this list now too


def pair_age_converter(final_parsed_list):

    now = datetime.now(timezone.utc)

    for item in final_parsed_list:
        unix_ms = item["Pair Age"]
        
        
        if not unix_ms:
            item["Pair Age"] = "N/A"
            continue
        
        creation_date = datetime.fromtimestamp(unix_ms / 1000.0, tz=timezone.utc)
        age_td = now - creation_date

        days = age_td.days
        hours, remainder = divmod(age_td.seconds, 3600)
        minutes, _ = divmod(remainder, 60)

        if days > 0:
            item["Pair Age"] = f"{days}d"
        elif hours > 0:
            item["Pair Age"] = f"{hours}h"
        else:
            item["Pair Age"] = f"{minutes}m"

    return final_parsed_list


def print_to_terminal(token_list):
    # Initialize the Rich console engine
    console = Console()

    # Create a stylized table structure
    table = Table(show_header=True, header_style="bold cyan", box=None)

    # Define columns with custom styling and text behaviors
    table.add_column("Token Name", style="white", no_wrap=True)
    table.add_column("Chain", style="green")
    table.add_column("Market Cap ($)", justify="right", style="yellow")
    table.add_column("Liquidity ($)", justify="right", style="cyan")
    table.add_column("24h Volume ($)", justify="right", style="yellow")
    table.add_column("Pair Age", justify="center", style="magenta")
    table.add_column("Dex", style="blue")
    table.add_column("Contract Address", style="dim white")

    for token in token_list:
        # Keep name truncation logic to prevent name stretching
        raw_name = token["Token Name"]
        clean_name = (raw_name[:12] + "...") if len(raw_name) > 15 else raw_name

        # Format metrics neatly
        market_cap = f"{token['Market Cap']:,}" if token["Market Cap"] else "N/A"
        volume_24h = f"{token['24h Volume']:,}" if token["24h Volume"] else "N/A"
        liquidity = f"{token['Liquidity']:,}" if token["Liquidity"] else "N/A"
        
        # Inject the row straight into the Rich matrix
        table.add_row(
            clean_name,
            token["Chain"].upper(),
            market_cap,
            liquidity,
            volume_24h,
            token["Pair Age"],
            token["Dex"],
            token["Contract Address"],  # Stays raw and untouched
        )

    # Print a clean layout block to the screen
    console.print("\n")
    console.print(table)
    console.print("\n")


#  ========= EXECUTION ========
recent_tokens = fetch_active_tokens()
ca_list = tokens_parser(recent_tokens)
jsonn_payload = bulk_metric_retrieval(ca_list)
token_list = minimalist_metric_parser(jsonn_payload)
final_list = pair_age_converter(token_list)

print_to_terminal(final_list)