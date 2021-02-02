import time
import json
from utils import start_logger
from typing import List
from datetime import datetime
from td.client import TDClient
from options import Instrument
from utils import get_param
import logging

logger = start_logger("account")

class Watchlist:

    def __init__(self, client, name, remote=True):
        self.td_client = client
        self.instruments = {'EQUITY': [], 'ETF': []}
        self.raw = None

        if not remote:
            with open(name) as local_watchlist:
                symbols = local_watchlist.read().strip().split('\n')
                for symbol in symbols:
                    processed = Instrument(self.td_client, symbol)
                    self.instruments['EQUITY'].append(processed)

        else:

            lists = self.td_client.get_watchlist_accounts('all')

            for watchlist in lists:
                if watchlist['name'] == name:
                    account_id = watchlist['accountId']
                    watchlist_id = watchlist['watchlistId']
                    self.raw = self.td_client.get_watchlist(account=account_id, watchlist_id=watchlist_id)

            if not self.raw:
                print("No watchlist found: %s" % name)

                # The watchlist "Russell 1k" is special case and we should create that one if it doesn't exist
                if name == "Russell 1k":
                    logger.info("The watchlist 'Russell 1k' is provided as a text file in this project. Run create_watchlist.py --name 'Russell 1k' --symbols russell-1k.txt to create it.")
            else:
                self.process_raw_watchlist(self.raw)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()

    def _write(self, title, data):
        dt = datetime.strftime(datetime.now(), "%d %b %Y %I-%M-%S")
        filename = "%s %s.json" % (title, dt)
        outfile = open(filename, 'w')

        outfile.write(json.dumps(data))
        outfile.close()

    def write_strikes_json(self):
        strikes = []
        for instrument in self.instruments['EQUITY']:
            for expiration in instrument.strike_dict():
                for strike in expiration:
                    strikes.append(strike)

        self._write("Option Chain", strikes)

    def write_quotes(self):
        quotes = []
        for instrument in self.instruments['EQUITY']:
            quotes.append(instrument.quote)

        self._write("Quotes", quotes)

    def get_spreads(self):

        # need to add searching/filtering from this level. Not buried in the classes
        # list of dicts (each item is an instrument), where each key is a date and values are lists of VerticalSpreads
        instrument_spreads = self.analyze_strategy()

        spread_json: List[str] = []

        # instrument spreads is a dict with a bunch of instrument expiration dates
        for instrument in instrument_spreads:
            # these are for logging
            # at this level we don't know what the symbol is so this will be set if there are any expiration dates in the dict
            # probably a cleaner way to do this...
            symbol = ""
            count = 0

            # loop through all the expiration dates
            for exp_date, spreads in instrument.items():

                # set the symbol now that we have expiration dates to look at
                if not symbol:
                    symbol = exp_date.symbol

                # loop through all spreads in for an expiration date
                for vert_spread in spreads:

                    # only show acceptable trades
                    # no score of 0 is considered acceptable
                    if vert_spread.score > 0:
                        spread_json.append(vert_spread.to_dict())

                        count += 1

            logger.info("Accepted %s spreads for %s" % (count, symbol))

        return spread_json

    def all(self):
        instruments = []
        for types, instrument_list in self.instruments.items():
            for instrument in instrument_list:
                instruments.append(instrument)

        return instruments

    def process_raw_watchlist(self, raw_watchlist: dict) -> None:
        self.account_id = raw_watchlist['accountId']
        self.name = raw_watchlist['name']
        self.watchlist_id = raw_watchlist['watchlistId']

        rate_limit = 120
        rate_delay = 0
        watchlist_count = len(raw_watchlist['watchlistItems'])

        if watchlist_count > rate_limit:
            # rate delay is .1 in microseconds
            rate_delay = 500000

        for item in raw_watchlist['watchlistItems']:
            instrument_dict = item['instrument']
            instrument_type = instrument_dict['assetType']
            symbol = instrument_dict['symbol']

            start = datetime.now()
            instrument = Instrument(self.td_client, symbol)
            end = datetime.now()
            elapsed = (end - start).microseconds
            if elapsed < rate_delay:
                time.sleep(.5)

            if instrument.quote:
                self.instruments[instrument_type].append(instrument)

    def analyze_strategy(self):
        spreads = []
        for instrument in self.all():
            logger.info("Analyzing symbol: %s" % instrument)
            put_spreads, call_spreads = instrument.analyze_strategies()
            spreads.append(put_spreads)
            spreads.append(call_spreads)

        return spreads


class TDAuth:

    def __init__(self):
        client_file = open('tda.txt', 'r')
        client_id = client_file.read().strip()
        client_file.close()

        # Create a new session, credentials path is optional.
        self.td_client = TDClient(
            client_id=client_id,
            redirect_uri='http://localhost',
            credentials_path='creds.txt'
        )

        # Login to the session
        self.td_client.login()

    def get_account_id(self):
        accounts = self.td_client.get_accounts()
        account_id = accounts[0]['securitiesAccount']['accountId']
        return account_id


def get_watchlist(options):
    # initialize connection with TD ameritrade account
    td_client = TDAuth()

    # get the local or remote watchlist name
    if options.local:
        watchlist_name = get_param('local watchlist')
    if options.remote:
        watchlist_name = get_param('remote watchlist')

    # pull the local or remote watchlist and get option chains for each symbol
    watchlist = Watchlist(td_client.td_client, watchlist_name, remote=options.remote)

    return watchlist

