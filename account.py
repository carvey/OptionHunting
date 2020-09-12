from td.client import TDClient
from options import Instrument
import logging


# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class Watchlist:

    def __init__(self, client, name):
        self.td_client = client
        self.instruments = {'EQUITY': [], 'ETF': []}
        self.raw = None

        lists = self.td_client.get_watchlist_accounts('all')

        for watchlist in lists:
            if watchlist['name'] == name:
                account_id = watchlist['accountId']
                watchlist_id = watchlist['watchlistId']
                self.raw = self.td_client.get_watchlist(account=account_id, watchlist_id=watchlist_id)

        if not self.raw:
            print("No watchlist found: %s" % name)
        else:
            self.process_raw_watchlist(self.raw)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()

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

        for item in raw_watchlist['watchlistItems']:
            instrument_dict = item['instrument']
            instrument_type = instrument_dict['assetType']
            symbol = instrument_dict['symbol']

            instrument = Instrument(self.td_client, symbol)

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

