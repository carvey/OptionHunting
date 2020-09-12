import logging
import optparse
import json
from utils import get_param
from account import TDAuth, Watchlist
from options import VertSpread
from typing import List
from datetime import datetime

# create logger
logger = logging.getLogger("raw")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

parser = optparse.OptionParser("usage: %prog [-t]")
parser.add_option('-t', "--test", action="store_true", dest="test", default=False)
options, args = parser.parse_args()

td_client = TDAuth().td_client

if options.test:
    watchlist = Watchlist(td_client, get_param('test watchlist'))
else:
    watchlist = Watchlist(td_client, get_param('watchlist'))

# need to add searching/filtering from this level. Not buried in the classes
# list of dicts (each item is an instrument), where each key is a date and values are lists of VerticalSpreads
instrument_spreads = watchlist.analyze_strategy()

dt = datetime.strftime(datetime.now(), "%d %b %Y %I-%M-%S")
filename = "Option Hunter %s.json" % dt
outfile = open(filename, 'w')

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

    logger.info("Wrote %s %s spreads to %s.xlsx" % (count, symbol, filename))

outfile.write(json.dumps(spread_json))
outfile.close()

