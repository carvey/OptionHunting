import logging
import optparse
import json
from utils import get_param
from account import TDAuth, Watchlist
from options import VertSpread
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

# write all the raw strikes to a json file
watchlist.write_strikes_json()
watchlist.write_quotes()

spreads = watchlist.get_spreads()

dt = datetime.strftime(datetime.now(), "%d %b %Y %I-%M-%S")
filename = "Option Hunter %s.json" % dt
outfile = open(filename, 'w')

outfile.write(json.dumps(spreads))
outfile.close()
