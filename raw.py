import logging
import optparse
import json
from utils import get_param, start_logger, define_parser
from account import get_watchlist
from options import VertSpread
from datetime import datetime

logger = start_logger("raw")

options, args = define_parser()

# initialize TDA connection and get the appropriate watchlist
watchlist = get_watchlist(options)

# write all the raw strikes to a json file
watchlist.write_strikes_json()
watchlist.write_quotes()

spreads = watchlist.get_spreads()

dt = datetime.strftime(datetime.now(), "%d %b %Y %I-%M-%S")
filename = "Option Hunter %s.json" % dt
outfile = open(filename, 'w')

outfile.write(json.dumps(spreads))
outfile.close()
