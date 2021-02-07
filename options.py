import json
import logging
from math import sqrt
from utils import get_param, start_logger
from datetime import datetime, timedelta
from td.option_chain import OptionChain as OptionParams
from itertools import combinations

logger = start_logger("options")

class OptionChain:

    def __init__(self, client, symbol: str):
        self.td_client = client
        logger.info("Building Options Chain for: %s" % symbol)
        date_range = datetime.today() + timedelta(get_param('search days'))
        self.params = OptionParams(symbol=symbol, strategy="SINGLE",  opt_range='otm',
                                   to_date=date_range, include_quotes="TRUE")
        self.params.validate_chain()

        self.dates = []

        self.chain_raw = self.td_client.get_options_chain(option_chain=self.params)

        self.process_raw_chain(self.chain_raw)

        strike_count = 0
        for date in self.dates:
            strike_count += len(date)

        logger.info("Pulled %s expiration dates and %s strikes" % (len(self.dates), strike_count))

    def process_raw_chain(self, chain_raw: dict):
        self.symbol = chain_raw['symbol']
        self.num_contracts = chain_raw['numberOfContracts']
        self.interest = chain_raw['interestRate']

        self.underlying = chain_raw['underlying']

        # Assumption is made that putExpDateMap and callExpDateMap will have the same keys (expiration dates)
        # has proved true so far but possible edge case
        for exp_date in chain_raw['putExpDateMap']:
            exp_datetime = self.clean_exp_format(exp_date)
            # Only add an expiration date if it comes with a put and call. Does this make sense?
            if exp_date in chain_raw['putExpDateMap'] and exp_date in chain_raw['callExpDateMap']:
                calls = chain_raw['callExpDateMap'][exp_date]
                puts = chain_raw['putExpDateMap'][exp_date]
                expiration = OptionExpDate(self.symbol, exp_datetime, puts, calls)
                self.dates.append(expiration)

    def clean_exp_format(self, expiration_str: str):
        expiration_str = expiration_str.split(":")[0]
        expiration = datetime.strptime(expiration_str, "%Y-%m-%d")
        formatted = expiration.strftime("%d %b %y")
        return formatted

    def expirations_to_dicts(self):
        dates = []
        for date in self.dates:
            dates.append(date.strikes_to_dicts())

        return dates

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

    def __init__(self, symbol: str, expiration: str, put_dates: dict, call_dates: dict):
        self.expiration = expiration
        self.symbol = symbol

        self.calls = []
        self.puts = []

        self.process_raw_date(put_dates, call_dates)

    def __str__(self) -> str:
        return "%s(%s)" % (self.symbol, self.expiration)

    def __repr__(self) -> str:
        return self.__str__()

    def __len__(self):
        return len(self.calls) + len(self.puts)

    def strikes_to_dicts(self):
        strikes = []
        for call in self.calls:
            strikes.append(call.to_dict())

        for put in self.puts:
            strikes.append(put.to_dict())

        return strikes

    def process_raw_date(self, put_dates: dict, call_dates) -> None:
        for strike, strike_data in call_dates.items():
            self.calls.append(OptionStrike(strike, strike_data[0]))

        for strike, strike_data in put_dates.items():
            self.puts.append(OptionStrike(strike, strike_data[0]))


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

    def to_dict(self):
        return {
            "symbol": self.symbol,
            "ul_symbol": self.description.split(" ")[0],
            "expiration_date": self.expiration_date,
            "strike": self.strikePrice,
            "dte": self.daysToExpiration,
            "put_call": self.putCall,
            "ask": self.ask,
            "bid": self.bid,
            "last": self.last,
            "net_change": self.netChange,
            "percent_change": self.percentChange,
            "low_price": self.lowPrice,
            "high_price": self.highPrice,
            "open_interest": self.openInterest,
            "volume": self.totalVolume,
            "delta": self.delta,
            "gamma": self.gamma,
            "theta": self.theta,
            "vega": self.vega,
            "rho": self.rho,
            "time_value": self.timeValue
        }

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

        self.expiration_date = ' '.join(self.description.split()[1:3])

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
    field_names = []

    def __init__(self, instrument, short_opt: OptionStrike, long_opt: OptionStrike):
        """
        For vertical put credit spreads we sell a put at a higher strike and buy a put at a lower strike
        """
        self.instrument = instrument
        self.short = short_opt
        self.long = long_opt

        self.description = "%s / %s" % (self.short.description, self.long.description)
        self.underlying_symbol = self.description.split(' ')[0]
        self.expiration = ' '.join(self.description.split(' ')[1:4])

        # Greeks!
        self.net_delta = round(self.short.delta - self.long.delta, 5)
        self.net_theta = round(self.short.theta - self.long.theta, 5)
        self.net_gamma = round(self.short.gamma - self.long.gamma, 5)
        self.net_vega = round(self.short.vega - self.long.gamma, 5)

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

    def _calculate_score(self, rr, pop, potm, ba_spread):
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
        score += score * (potm / 100)

        # we only want tight bid/ask spreads. The ba_spread value should be the sum of the short and long b/a spread
        # here we subtract the total bid/ask spread times the score from the score.
        # this effectively subtracts the b/a spread as a percentage of the total score
        # this means that any total bid ask spread >= 1 will result in a negative score and be filtered out
        # .02 is the lowest possible ba_spread (both short and long b/a spreads are one cent apart) which will subtract 2% off the score. Fix this comment later
        # this is very aggressive and might need to be toned down some. TBD
        score = score - (score * ba_spread)
        
        return round(score, 2)

    def analyze(self) -> None:

        self.net_credit = self._calculate_credit()
        self.profit = round(self.net_credit * 100, 2)

        self.risk = round((self.strike_spread - self.net_credit) * 100, 2)

        # this happens sometimes and I have no idea what to do about it
        if round(self.strike_spread, 5) == round(self.net_credit, 5):
            self.rr = -1
        else:
            # risk/reward ratio
            self.rr = round((self.profit / self.risk) * 100, 2)

        # prob of profit
        #self.pop = round(100 - (self.net_credit / self.strike_spread) * 100, 1)
        self.pop = round(100 - (abs(self.short.delta) * 100), 2)

        # percent OTM
        self.potm = abs(round(100 - ((self.short.strikePrice / self.instrument.last) * 100), 2))

        self.total_spread = round(self.short.spread + self.long.spread, 5)
        self.avg_volume = (self.short.totalVolume + self.long.totalVolume) / 2

        # aggregated risk score. Needs improvement.
        self.score = self._calculate_score(self.rr, self.pop, self.potm, self.total_spread)

        # euro style IV until I figure out American. Can hopefully approximate
        # this is also IV of short. Need to figure out how to combine for a spread or instrument
        #self.iv = BS([self.instrument.last, self.short.strikePrice, 0, self.short.daysToExpiration], putPrice=self.short.mid).impliedVolatility

    def setup_field_names(self):
        """
        Output the following fields when printing:
        symbol, expiration date, short strike, long strike, net credit, profit, max loss, rr, pop, score

        """
        columns = ["Symbol", "Type", "DTE", "Expiration Date", "S. Strike", "L. Strike", "UL Last", "% OTM", "UL Low",
                   "UL High", "Net Credit", "Premium", "Max Loss", "R/R", "POP", "Score",
                   "L. B/A Spread", "S. B/A Spread", "Total B/A Spread",
                   "L. Volume", "S. Volume", "Avg Volume",
                   "S. Open Interest", "L. Open Interest",
                   "S. Delta", "L. Delta", "Net Delta",
                   "S. Theta", "L. Theta", "Net Theta",
                   "S. Gamma", "L. Gamma", "Net Gamma",
                   "S. Vega", "L. Vega", "Net Vega", "Assumption"]

        for column in columns:
            if column not in VertSpread.field_names:
                VertSpread.field_names.append(column)

    def details(self):
        """
        This function exists for a reason I can't recall
        TODO: remember why I made this a seperate function and comment better next time

        :return:
        """
        return [self.underlying_symbol, self.type, self.short.daysToExpiration, self.expiration, self.short.strikePrice,
                self.long.strikePrice,
                self.instrument.last, self.potm, self.instrument.low, self.instrument.high,
                self.net_credit, self.profit, self.risk, self.rr, self.pop, self.score,
                self.long.spread, self.short.spread, self.total_spread,
                self.long.totalVolume, self.short.totalVolume, self.avg_volume,
                self.short.openInterest, self.long.openInterest,
                self.short.delta, self.long.delta, self.net_delta, self.short.theta, self.long.theta, self.net_theta,
                self.short.gamma, self.long.gamma, self.net_gamma, self.short.vega, self.long.vega, self.net_vega, self.assumption]

    def acceptable(self):
        option_budget = get_param('account size')
        acceptable_risk_percent = get_param('max risk per trade')
        acceptable_risk = option_budget * (acceptable_risk_percent / 100)

        #avg_volume = (self.long.totalVolume + self.short.totalVolume) / 2

        # only add this as an acceptable trade if the max loss is in the acceptable range
        if self.risk <= acceptable_risk:
            if self.total_spread > 0:
                if self.net_credit > 0:
                    #if avg_volume >= 100:
                    if self.short.totalVolume > 100 and self.long.totalVolume > 100:
                        if self.long.openInterest > 1000 and self.short.openInterest > 1000:
                            return True
        return False

    def to_dict(self):
        spread: dict = dict(zip(self.field_names, self.details()))

        return spread

    def to_json(self):
        spread = self.to_dict()
        return json.dumps(spread)

class PutCreditSpread(VertSpread):

    def __init__(self, *args, **kwargs):

        super(PutCreditSpread, self).__init__(*args, **kwargs)
        self.type = "PCS"
        self.assumption = "Bullish"
        self.strike_spread = round(self.short.strikePrice - self.long.strikePrice, 3)

        self.analyze()

        self.setup_field_names()

    @staticmethod
    def analyze_trades(instrument, exp_dates: list) -> dict:
        spreads = {}
        spread_count = 0
        for date in exp_dates:
            spreads[date] = []

            # group all the strikes into overlapping pairs of 2
            # and don't get the last one
            # ex: [1, 2, 3] would turn into [[1, 2], [2, 3]]
            grouped_spreads = list(combinations(date.puts, 2))
            spread_count += len(grouped_spreads)

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

                put_spread = PutCreditSpread(instrument, short_leg, long_leg)

                if put_spread.acceptable():
                    spreads[date].append(put_spread)

        logger.info("Analyzed %s spreads for %s" % (spread_count, instrument.symbol))
        return spreads


class CallCreditSpread(VertSpread):

    def __init__(self, *args, **kwargs):
        super(CallCreditSpread, self).__init__(*args, **kwargs)

        self.type = "CCS"
        self.assumption = "Bearish"
        self.strike_spread = round(self.long.strikePrice - self.short.strikePrice, 3)
        self.analyze()
        self.setup_field_names()

    @staticmethod
    def analyze_trades(instrument, exp_dates: list) -> dict:
        spreads = {}
        for date in exp_dates:
            spreads[date] = []

            # group all the strikes into overlapping pairs of 2
            # and don't get the last one
            # ex: [1, 2, 3] would turn into [[1, 2], [2, 3]]

            grouped_spreads = list(combinations(date.calls, 2))
            for raw_spread in grouped_spreads:

                # we're looking at all combinations of strikes so we don't know which
                # order the long and short leg will be in
                if raw_spread[0].strikePrice < raw_spread[1].strikePrice:
                    short_leg = raw_spread[0]
                    long_leg = raw_spread[1]
                else:
                    short_leg = raw_spread[1]
                    long_leg = raw_spread[0]

                # validate that these aren't the same option. APIs be weird sometimes
                if short_leg.description == long_leg.description:
                    continue

                call_spread = CallCreditSpread(instrument, short_leg, long_leg)

                if call_spread.acceptable():
                    spreads[date].append(call_spread)

        return spreads


class IronCondor:
    pass


class Instrument:

    def __init__(self, client, symbol):
        self.td_client = client
        self.symbol = symbol
        self.chain = OptionChain(self.td_client, self.symbol)

        self.quote = self.chain.underlying
        if self.quote:
            self.last = self.quote['last']
            self.low = self.quote['lowPrice']
            self.high = self.quote['highPrice']

    def __str__(self):
        return self.symbol

    def __repr__(self):
        return self.__str__()

    def strike_dict(self):
        return self.chain.expirations_to_dicts()

    def analyze_CCS(self):
        # note that this search will only be able to filter down raw option dicts
        # NOT VertSpread instances that have been enriched
        #trades = self.chain.search(delta=[-.35, 0])

        call_spreads = CallCreditSpread.analyze_trades(self, self.chain.dates)
        return call_spreads

    def analyze_PCS(self):
        # note that this search will only be able to filter down raw option dicts
        # NOT VertSpread instances that have been enriched
        #trades = self.chain.search(delta=[-.35, 0])

        put_spreads = PutCreditSpread.analyze_trades(self, self.chain.dates)
        return put_spreads
