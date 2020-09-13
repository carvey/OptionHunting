import json
import logging
import argparse
import urllib3
from utils import get_param
from openpyxl import Workbook
from account import TDAuth, Watchlist
from datetime import datetime

# create logger
logger = logging.getLogger("create_watchlist")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

parser = argparse.ArgumentParser("usage: %prog")
parser.add_argument('-s', "--symbols", dest="symbols", required=True)
parser.add_argument('-n', "--name", dest="name", required=True)
options = parser.parse_args()

td_client = TDAuth()

symbols = []
symbol_file = open(options.symbols)
for symbol in symbol_file.readlines():
    watchlist_item = {
        "instrument": {
            "symbol": symbol.strip(),
            "assetType": "EQUITY"
        }
    }
    symbols.append(watchlist_item)

symbol_file.close()

"""
The API expects watchlistItems to be a list of dicts of format:
[
    {
        "instrument": 
        {
            "symbol": 'SOME-SYMBOL-NAME',
            "assetType": "EQUITY"
        }
    },
    
    ...
]
"""
account_id = td_client.get_account_id()
td_client.td_client.create_watchlist(account=account_id, name=options.name, watchlistItems=symbols)
logger.info("Watchlist '%s' created from %s" % (options.name, options.symbols))
