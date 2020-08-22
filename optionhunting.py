# Import the client
import pprint
import sys
import logging
from mibian import BS
from itertools import combinations
from openpyxl import Workbook
from td.client import TDClient
from td.option_chain import OptionChain as OptionParams
from datetime import datetime, timedelta

# Note: reddit user says TDA API rate limit is 120 calls / minute

"""
Need to:
    1) pull down account status
    2) display option details (with TOMIC constraints)
    3) display account positions
    4) search for options that meet TOMIC criteria
    5) analyze options down a watchlist for RR and %OTM viable vertical credit spreads
    6) write out a bunch of columns
    7) add DTE on vert spreads
    8) calculate %OTM
    9) figure out POP / RR metric
    10) add in days since underlying last hit short leg strike
    11) filter for open interest
    12) do something with IV
    13) fix scoring metric (reduce delta)
    14) All options for a given date have permutations made and analyzed
    15) fix str and repr since excel works now
    16) add days since last hitting strike
    17) set trade critera (account size, max acceptable loss)
    18) add greeks short, long, and net to excel
    19) add beta for each symbol
    20) add a sheet for fundamentals
"""

# create logger
logger = logging.getLogger('optionhunting')
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class OptionChain:

    def __init__(self, symbol: str):
        date_range = datetime.today() + timedelta(50)
        self.params = OptionParams(symbol=symbol, strategy="SINGLE", contract_type="PUT", opt_range='otm',
                                   to_date=date_range, include_quotes="TRUE")
        self.params.validate_chain()

        self.dates = []

        chain_raw = TDSession.get_options_chain(option_chain=self.params)
        self.process_raw_chain(chain_raw)

    def process_raw_chain(self, chain_raw: dict):
        self.symbol = chain_raw['symbol']
        self.num_contracts = chain_raw['numberOfContracts']
        self.interest = chain_raw['interestRate']

        for exp_date in chain_raw['putExpDateMap']:
            exp_datetime = self.clean_exp_format(exp_date)
            self.dates.append(OptionExpDate(self.symbol, exp_datetime, chain_raw['putExpDateMap'][exp_date]))

    def clean_exp_format(self, expiration_str: str):
        expiration_str = expiration_str.split(":")[0]
        expiration = datetime.strptime(expiration_str, "%Y-%m-%d")
        formatted = expiration.strftime("%d %b %y")
        return formatted

    def search(self, **kwargs):
        strikes = {}

        for option_key, option_val in kwargs.items():
            for date in self.dates:

                if date not in strikes:
                    strikes[date] = []

                for strike in date.strikes:
                    attr = getattr(strike, option_key)
                    if attr == 'NaN':
                        strikes[date].append(strike)
                        continue

                    if attr > option_val[0] and attr < option_val[1]:
                        strikes[date].append(strike)

        return strikes


class OptionExpDate:

    def __init__(self, symbol: str, expiration: str, raw_date: dict):
        self.expiration = expiration
        self.symbol = symbol
        self.strikes = []

        self.process_raw_date(raw_date)

    def __str__(self) -> str:
        return "%s(%s)" % (self.symbol, self.expiration)

    def __repr__(self) -> str:
        return self.__str__()

    def process_raw_date(self, raw_date: dict) -> None:
        for strike, strike_data in raw_date.items():
            self.strikes.append(OptionStrike(strike, strike_data[0]))


class OptionStrike:

    def __init__(self, strike: str, raw_strike: dict):
        self.strike = strike
        self.raw = raw_strike
        self.process_raw_strike(raw_strike)

    def __str__(self) -> str:
        return "%s" % self.description

    def __repr__(self) -> str:
        return self.__str__()

    def process_raw_strike(self, raw_strike: dict):
        """
        This should assign the following attributes to instances of this class (values are a sample)
        'ask': 1.82,
        'askSize': 1,
        'bid': 1.7,
        'bidAskSize': '1X1',
        'bidSize': 1,
        'closePrice': 1.76,
        'daysToExpiration': 6,
        'deliverableNote': '',
        'delta': -0.321,
        'description': 'MSFT Aug 21 2020 205 Put',
        'exchangeName': 'OPR',
        'expirationDate': 1598040000000,
        'expirationType': 'R',
        'gamma': 0.043,
        'highPrice': 2.7,
        'inTheMoney': False,
        'isIndexOption': None,
        'last': 1.74,
        'lastSize': 0,
        'lastTradingDay': 1598054400000,
        'lowPrice': 1.62,
        'mark': 1.76,
        'markChange': 0.0,
        'markPercentChange': 0.0,
        'mini': False,
        'multiplier': 100.0,
        'netChange': -0.66,
        'nonStandard': False,
        'openInterest': 12431,
        'openPrice': 0.0,
        'optionDeliverablesList': None,
        'percentChange': -37.5,
        'putCall': 'PUT',
        'quoteTimeInLong': 1597435199692,
        'rho': -0.013,
        'settlementType': ' ',
        'strikePrice': 205.0,
        'symbol': 'MSFT_082120P205',
        'theoreticalOptionValue': 1.76,
        'theoreticalVolatility': 29.0,
        'theta': -0.213,
        'timeValue': 1.74,
        'totalVolume': 4597,
        'tradeDate': None,
        'tradeTimeInLong': 1597435198391,
        'vega': 0.103,
        'volatility': 28.607}
        """
        for key, val in raw_strike.items():
            setattr(self, key, val)

        self.spread = self.ask - self.bid
        self.mid = (self.ask + self.bid) / 2


class VertSpread:
    print_fields = []

    def __init__(self, instrument, short_opt: OptionStrike, long_opt: OptionStrike):
        """
        For vertical put credit spreads we sell a put at a higher strike and buy a put at a lower strike
        """
        self.instrument = instrument
        self.short = short_opt
        self.long = long_opt
        self.analyze()

        self.setup_print_fields()

    def __str__(self) -> str:
        return "%s %s %s/%s" % (self.symbol, self.expiration, self.short.strikePrice, self.long.strikePrice)

    def __repr__(self) -> str:
        return self.__str__()

    def calculate_credit(self) -> int:

        cost = round(self.short.mid - self.long.mid, 2)
        # going to play with last sale instead. Maybe better for after hours?
        # cost = round(self.short.last - self.long.last, 2)

        return cost

    def analyze(self) -> None:
        self.description = "%s / %s" % (self.short.description, self.long.description)
        self.underlying_symbol = self.description.split(' ')[0]
        self.expiration = ' '.join(self.description.split(' ')[1:4])

        self.net_credit = self.calculate_credit()
        self.profit = round(self.net_credit * 100, 2)

        self.strike_spread = self.short.strikePrice - self.long.strikePrice
        self.risk = round((self.strike_spread - self.net_credit) * 100, 2)

        # this happens sometimes and I have no idea what to do about it
        if self.strike_spread == self.net_credit:
            self.rr = -1
        else:
            # risk/reward ratio
            self.rr = round((self.profit / self.risk) * 100, 2)

        # prob of profit
        self.pop = round(100 - (self.net_credit / self.strike_spread) * 100, 1)

        # percent OTM
        # self.potm = round(100 - (self.short.StrikePrice/self.), 2)

        # aggregated risk score. Needs improvement.
        self.score = round((self.risk + self.rr) / 2, 2)

        self.total_spread = self.short.spread + self.long.spread
        self.avg_volume = (self.short.totalVolume + self.long.totalVolume) / 2

        # percent OTM
        self.potm = round(100 - ((self.short.strikePrice / self.instrument.ul_last) * 100), 2)

    def setup_print_fields(self):
        """
        Output the following fields when printing:
        symbol, expiration date, short strike, long strike, net credit, profit, max loss, rr, pop, score

        """
        columns = ["Symbol", "DTE", "Expiration Date", "Short Strike", "Long Strike", "UL Last", "% OTM", "UL Low",
                   "UL High",
                   "L. Open Interest", "Net Credit", "Premium", "Max Loss", "RR Ratio", "POP", "Score", "Long Spread",
                   "Short Spread", "Total Spread", "Long Volume", "Short Volume", "Avg Volume"]

        for column in columns:
            if column not in VertSpread.print_fields:
                VertSpread.print_fields.append(column)

    def details(self):
        return [self.underlying_symbol, self.short.daysToExpiration, self.expiration, self.short.strikePrice,
                self.long.strikePrice,
                self.instrument.ul_last, self.potm, self.instrument.ul_low, self.instrument.ul_high,
                self.long.openInterest,
                self.net_credit, self.profit, self.risk, self.rr, self.pop, self.score, self.long.spread,
                self.short.spread,
                self.total_spread, self.long.totalVolume, self.short.totalVolume, self.avg_volume]

    def acceptable(self):

        option_budget = int(sys.argv[1])
        acceptable_risk_percent = 9
        acceptable_risk = option_budget * (acceptable_risk_percent / 100)

        avg_volume = (self.long.totalVolume + self.short.totalVolume) / 2

        # only add this as an acceptable trade if the max loss is in the acceptable range
        if self.risk <= acceptable_risk:
            if self.net_credit > 0:
                if avg_volume >= 100:
                    if self.long.openInterest > 1000 and self.short.openInterest > 1000:
                        return True

        return False

    @staticmethod
    def analyze_trades(instrument, exp_dates: OptionExpDate) -> dict:
        spreads = {}
        for date, strikes in exp_dates.items():
            spreads[date] = []
            # group all the strikes into overlapping pairs of 2
            # and don't get the last one
            # ex: [1, 2, 3] would turn into [[1, 2], [2, 3]]
            # pdb.set_trace()

            grouped_spreads = list(combinations(strikes, 2))
            for raw_spread in grouped_spreads:

                # we're looking at all combinations of strikes so we don't know which
                # order the long and short leg will be in
                if raw_spread[0].strikePrice > raw_spread[1].strikePrice:
                    short_leg = raw_spread[0]
                    long_leg = raw_spread[1]
                else:
                    short_leg = raw_spread[1]
                    long_leg = raw_spread[0]

                # validate that these aren't the same option. APIs be weird sometimes
                if short_leg.description == long_leg.description:
                    continue

                spread = VertSpread(instrument, short_leg, long_leg)

                if spread.acceptable():
                    spreads[date].append(spread)

        return spreads


class Watchlist:

    def __init__(self, name):
        self.instruments = {'EQUITY': [], 'ETF': []}
        self.raw = None

        lists = TDSession.get_watchlist_accounts('all')

        for watchlist in lists:
            if watchlist['name'] == name:
                account_id = watchlist['accountId']
                watchlist_id = watchlist['watchlistId']
                self.raw = TDSession.get_watchlist(account=account_id, watchlist_id=watchlist_id)

        if not self.raw:
            print("No watchlist found: %s" % name)
        else:
            self.process_raw_watchlist(self.raw)

        self.enrich_instruments()

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

    def enrich_instruments(self):
        all_instruments = self.all()
        symbols = [instrument.symbol for instrument in all_instruments]

        """
        This will return a dict of stocks where each value contains:
          "symbol": "string",
          "description": "string",
          "bidPrice": 0,
          "bidSize": 0,
          "bidId": "string",
          "askPrice": 0,
          "askSize": 0,
          "askId": "string",
          "lastPrice": 0,
          "lastSize": 0,
          "lastId": "string",
          "openPrice": 0,
          "highPrice": 0,
          "lowPrice": 0,
          "closePrice": 0,
          "netChange": 0,
          "totalVolume": 0,
          "quoteTimeInLong": 0,
          "tradeTimeInLong": 0,
          "mark": 0,
          "exchange": "string",
          "exchangeName": "string",
          "marginable": false,
          "shortable": false,
          "volatility": 0,
          "digits": 0,
          "52WkHigh": 0,
          "52WkLow": 0,
          "peRatio": 0,
          "divAmount": 0,
          "divYield": 0,
          "divDate": "string",
          "securityStatus": "string",
          "regularMarketLastPrice": 0,
          "regularMarketLastSize": 0,
          "regularMarketNetChange": 0,
          "regularMarketTradeTimeInLong": 0
        """
        quotes = TDSession.get_quotes(instruments=symbols)

        for symbol, quote in quotes.items():
            # for some reason the TDA API is returning everything as an Equity and not delineating ETFs
            # hard code in meantime until reason is found or more elegant workaround is written
            # instrument_type = quote['assetType']
            instrument_type = "EQUITY"

            instrument_list = self.instruments[instrument_type]

            for instrument in instrument_list:
                if instrument.symbol == symbol:
                    instrument.ul_last = quote['lastPrice']
                    instrument.ul_high = quote['highPrice']
                    instrument.ul_low = quote['lowPrice']

    def process_raw_watchlist(self, raw_watchlist: dict) -> None:
        self.account_id = raw_watchlist['accountId']
        self.name = raw_watchlist['name']
        self.watchlist_id = raw_watchlist['watchlistId']

        for item in raw_watchlist['watchlistItems']:
            instrument_dict = item['instrument']
            instrument_type = instrument_dict['assetType']
            symbol = instrument_dict['symbol']

            instrument = Instrument(symbol)

            self.instruments[instrument_type].append(instrument)

    def analyze_strategy(self, Analyzer):
        spreads = []
        for instrument in self.all():
            logger.info("Analyzing symbol: %s" % instrument)
            spreads.append(instrument.analyze_strategy(Analyzer))

        return spreads


class Instrument:

    def __init__(self, symbol):
        self.symbol = symbol

    def __str__(self):
        return self.symbol

    def __repr__(self):
        return self.__str__()

    def analyze_strategy(self, Analyzer):
        chain = OptionChain(self.symbol)

        # note that this search will only be able to filter down raw option dicts
        # NOT VertSpread instances that have been enriched
        trades = chain.search(delta=[-.35, 0])

        spreads = Analyzer.analyze_trades(self, trades)

        return spreads


class ExcelFormatter:

    def __init__(self, document):
        self.wkbook = Workbook()
        self.sheet = self.wkbook.active

        self.filename = "%s.xlsx" % document

    def save(self):
        self.wkbook.save(filename=self.filename)

    def write(self, data: list, save=True):
        self.sheet.append(data)
        if save:
            self.save()


pp = pprint.PrettyPrinter(indent=4)

# Create a new session, credentials path is optional.
TDSession = TDClient(
    client_id='FAGNV1JVTHY0NS9SXYJGM8TJLTADWXSI',
    redirect_uri='http://localhost',
    credentials_path='creds2.txt'
)

# Login to the session
TDSession.login()

# this must be pulling from real account and not paper traded?
watchlist = Watchlist('Berkshire Hathaway')

# need to add searching/filtering from this level. Not buried in the classes
# list of dicts (each item is an instrument), where each key is a date and values are lists of VerticalSpreads
instrument_spreads = watchlist.analyze_strategy(VertSpread)

dt = str(datetime.now()).split('.')[0]
log = ExcelFormatter("log %s" % dt)
log.write(VertSpread.print_fields)

for instrument in instrument_spreads:
    for exp_date, spreads in instrument.items():
        for vert_spread in spreads:
            details = vert_spread.details()
            log.write(details, False)

log.save()
