#! /usr/bin/python3

import os
import logging
import optparse
import json
import time
import schedule
from raw import run_raw
from utils import get_param, start_logger, define_parser
from account import get_watchlist
from options import VertSpread
from datetime import datetime

logger = start_logger("hunterd")
options, args = define_parser()

logger.info("starting hunterd daemon")

run_frequency = get_param("run frequency mins")

# wrap the function with a log entry
def run_job():
    run_raw()
    logger.info(f"Pausing for {run_frequency} minutes")

schedule.every(run_frequency).minutes.do(run_job)

# run a job immediately
#run_job()

while True:
    # only run on weekdays
    if datetime.today().weekday() in range(0, 5):

        # only run between 9:00 - 5:00. Can fit to market hours later if we want.
        if datetime.today.hour in range(9, 17):

            # run a new job each amount of minutes specified by the user in parameters.txt
            schedule.run_pending()
            time.sleep(1)

    # check again in a minute if it's time to run jobs
    #logger.info("Not time to run jobs. Pausing 60s.")
    time.sleep(60)

# this wont get called for now
logger.info("stopping hunterd daemon")
