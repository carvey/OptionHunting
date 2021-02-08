import json
import requests
from utils import start_logger
from account import get_watchlist

logger = start_logger("account")

headers = {"Accept": "application/json, text/plain, */*", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36"}

r = requests.get("https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true", headers=headers)

symbols = []

if r.status_code == 200:
    rows = json.loads(r.content)["data"]["rows"]
    symbol_count = len(rows)
    logger.info(f"Processing {symbol_count} symbols")

    for row in rows:
        symbol = row['symbol']

        if "^" not in symbol and "/" not in symbol:
            symbols.append(symbol)

else:
    logger.error(f"Request failed with status: {r.status_code}")

with open("all-symbols.txt", "w") as symbols_fle:
    for symbol in symbols:
        symbols_fle.write(f"{symbol}\n")

# initialize TDA connection and get the appropriate watchlist
watchlist = get_watchlist(process_market=True)

# calculate all PCS and CCS vertical spreads
acceptable_symbols = watchlist.get_spreads(find_acceptable=True)

with open("watchlists/weekly-watchlist.txt", 'w') as weekly_watchlist:
    for symbol in acceptable_symbols:
        weekly_watchlist.write(f"{symbol}\n")
