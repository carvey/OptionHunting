import sys
import logging
from math import sqrt
from utils import get_param
from datetime import datetime, timedelta
from td.option_chain import OptionChain as OptionParams
from itertools import combinations

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class OptionChain:

    def __init__(self, client, symbol: str):
        self.td_client = client
        logger.info("Building Options Chain for: %s" % symbol)
        date_range = datetime.today() + timedelta(get_param('search days'))
        self.params = OptionParams(symbol=symbol, strategy="SINGLE", contract_type="PUT", opt_range='otm',
                                   to_date=date_range, include_quotes="TRUE")
        self.params.validate_chain()

        self.dates = []

        chain_raw = self.td_client.get_options_chain(option_chain=self.params)
        self.process_raw_chain(chain_raw)

        strike_count = 0
        for date in self.dates:
            strike_count += len(date)

        logger.info("Pulled %s expiration dates and %s strikes" % (len(self.dates), strike_count))

    def process_raw_chain(self, chain_raw: dict):
        self.symbol = chain_raw['symbol']
        self.num_contracts = chain_raw['numberOfContracts']
        self.interest = chain_raw['interestRate']

        self.underlying = chain_raw['underlying']

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

    def __len__(self):
        return len(self.strikes)

    def process_raw_date(self, raw_date: dict) -> None:
        for strike, strike_data in raw_date.items():
            self.strikes.append(OptionStrike(strike, strike_data[0]))


class OptionStrike:

    def __init__(self, strike: str, raw_strike: dict):
        self.strike = strike
        self.raw = raw_strike
        self.process_raw_strike(raw_strike)
        self.validate_greeks()

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

    def validate_greeks(self):
        """
        for some reason the TDA app doesn't always return the greeks for a strike
        set 0 instead of 'NaN' if this happens
        :return: None
        """
        if self.delta == 'NaN':
            self.delta = 0

        if self.theta == 'NaN':
            self.theta = 0

        if self.gamma == 'NaN':
            self.gamma = 0

        if self.vega == 'NaN':
            self.vega = 0


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
        return "%s %s %s/%s" % (self.instrument.symbol, self.expiration, self.short.strikePrice, self.long.strikePrice)

    def __repr__(self) -> str:
        return self.__str__()


    def _calculate_credit(self) -> int:

        cost = round(self.short.mid - self.long.mid, 2)
        # going to play with last sale instead. Maybe better for after hours?
        # cost = round(self.short.last - self.long.last, 2)

        return cost

    def _model_pop(self, pop):
        if pop <= 0:
            return 0

        # linear function used here
        # nothing below 40 is acceptable
        # divide by 12 to have the function equal 5 at pop=100
        return (pop - 40) / 12

    def _model_rr(self, rr):
        # anything with a reward/risk less than 10 is not within my acceptable levels of risk and
        # would throw a domain error (ValueError in python) if ran through this model
        if rr < 10:
            return 0
        else:
            # square root is used as the base function for this model
            # 10 is subtracted since no RR below that is acceptable
            # 20/sqrt(90) is used as a multiplier to ensure that this function equals 20 at rr=100
            return sqrt(rr-10) * (20/sqrt(90))

    def _calculate_score(self, rr, pop, potm):
        """
        The idea with this is to combine the reward/risk ratio and probability of profit to
        get a one-look estimate of how profitable the trade will be.

        Assumptions and risk are built into the model. So no RR < 10, and POP of anything < 40 is
        also discared. POP is given some allowance to account for differences in how POP is calculated.

        A score of 100 represents approximately 100% RR and 100% POP. If a score anywhere close to 100
        shows up the model should probably get a tuning.

        After running some tests, any score over 7.5 seems to be an interesting trade.
        """
        score = self._model_rr(rr) * self._model_pop(pop)

        # add the % OTM to the final score
        # ex if score = 25 and % OTM = 10 then the final score should be 27.5
        score += score * (potm/100)
        
        return round(score, 2)


    def analyze(self) -> None:
        self.description = "%s / %s" % (self.short.description, self.long.description)
        self.underlying_symbol = self.description.split(' ')[0]
        self.expiration = ' '.join(self.description.split(' ')[1:4])

        self.net_credit = self._calculate_credit()
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
        #self.pop = round(100 - (self.net_credit / self.strike_spread) * 100, 1)
        self.pop = round(100 - (abs(self.short.delta) * 100), 2)

        # percent OTM
        self.potm = round(100 - ((self.short.strikePrice / self.instrument.last) * 100), 2)

        # aggregated risk score. Needs improvement.
        self.score = self._calculate_score(self.rr, self.pop, self.potm)

        self.total_spread = self.short.spread + self.long.spread
        self.avg_volume = (self.short.totalVolume + self.long.totalVolume) / 2


        # Greeks!
        self.net_delta = self.short.delta - self.long.delta
        self.net_theta = self.short.theta - self.long.theta
        self.net_gamma = self.short.gamma - self.long.gamma
        self.net_vega = self.short.vega - self.long.gamma

        # euro style IV until I figure out American. Can hopefully approximate
        # this is also IV of short. Need to figure out how to combine for a spread or instrument
        #self.iv = BS([self.instrument.last, self.short.strikePrice, 0, self.short.daysToExpiration], putPrice=self.short.mid).impliedVolatility

    def setup_print_fields(self):
        """
        Output the following fields when printing:
        symbol, expiration date, short strike, long strike, net credit, profit, max loss, rr, pop, score

        """
        columns = ["Symbol", "DTE", "Expiration Date", "S. Strike", "L. Strike", "UL Last", "% OTM", "UL Low",
                   "UL High", "L. Open Interest", "Net Credit", "Premium", "Max Loss", "R/R", "POP", "Score", "L. Spread",
                   "S. Spread", "Total Spread", "L. Volume", "S. Volume", "Avg Volume", "S. Delta", "L. Delta", "Net Delta",
                   "S. Theta", "L. Theta", "Net Theta", "S. Gamma", "L. Gamma", "Net Gamma", "S. Vega", "L. Vega", "Net Vega"]

        for column in columns:
            if column not in VertSpread.print_fields:
                VertSpread.print_fields.append(column)

    def details(self):
        """
        This function exists for a reason I can't recall
        TODO: remember why I made this a seperate function and comment better next time

        :return:
        """
        return [self.underlying_symbol, self.short.daysToExpiration, self.expiration, self.short.strikePrice,
                self.long.strikePrice,
                self.instrument.last, self.potm, self.instrument.low, self.instrument.high,
                self.long.openInterest,
                self.net_credit, self.profit, self.risk, self.rr, self.pop, self.score, self.long.spread,
                self.short.spread,
                self.total_spread, self.long.totalVolume, self.short.totalVolume, self.avg_volume,
                self.short.delta, self.long.delta, self.net_delta, self.short.theta, self.long.theta, self.net_theta,
                self.short.gamma, self.long.gamma, self.net_gamma, self.short.vega, self.long.vega, self.net_vega]

    def acceptable(self):
        option_budget = get_param('account size')
        acceptable_risk_percent = get_param('max risk per trade')
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


class Instrument:

    def __init__(self, client, symbol):
        self.td_client = client
        self.symbol = symbol
        self.chain = OptionChain(self.td_client, self.symbol)

        self.quote = self.chain.underlying
        self.last = self.quote['last']
        self.low = self.quote['lowPrice']
        self.high = self.quote['highPrice']

    def __str__(self):
        return self.symbol

    def __repr__(self):
        return self.__str__()

    def analyze_strategy(self, Analyzer):
        # note that this search will only be able to filter down raw option dicts
        # NOT VertSpread instances that have been enriched
        trades = self.chain.search(delta=[-.35, 0])

        spreads = Analyzer.analyze_trades(self, trades)

        return spreads
