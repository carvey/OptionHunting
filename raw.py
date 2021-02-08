import os
import logging
import optparse
import json
from utils import get_param, start_logger, define_parser
from account import get_watchlist
from options import VertSpread
from datetime import datetime

logger = start_logger("raw")

options, args = define_parser()

def run_raw():
    # initialize TDA connection and get the appropriate watchlist
    watchlist = get_watchlist(options=options)

    # write all the raw strikes to a json file
    watchlist.write_strikes_json()
    watchlist.write_quotes()

    # calculate all PCS and CCS vertical spreads
    spreads = watchlist.get_spreads()

    # create a directory to store output data
    out_dir = "out-data/options-analyzed/"
    outdir = os.makedirs(out_dir, exist_ok=True)

    # generate a path to store the the analyzed option spreads
    dt = datetime.strftime(datetime.now(), "%d %b %Y %I-%M-%S")
    filename = "options-analyzed %s.json" % dt
    out_path = os.path.join(out_dir, filename)

    # write the analyzed spread data to a file in raw json
    outfile = open(out_path, 'w')
    outfile.write(json.dumps(spreads))
    outfile.close()

if __name__ == "__main__":
    run_raw()
