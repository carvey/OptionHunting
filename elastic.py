import os
import logging
import optparse
import json
import requests
from utils import get_param, start_logger, define_parser
from account import get_watchlist
from options import VertSpread
from datetime import datetime


logger = start_logger("elastic")

options, args = define_parser()

def run_elastic():
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
    dt = datetime.strftime(datetime.now(), "%Y-%m-%dT%H:%M:%S%z")
    filename = "options-analyzed %s.json" % dt
    out_path = os.path.join(out_dir, filename)

    for spread in spreads:
        spread['timestamp'] = dt
        r=requests.post("http://localhost:9200/options-analyzed/_doc/", json=spread)
        print(r.content)

if __name__ == "__main__":
    run_elastic()
