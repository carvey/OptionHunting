# Import the client
import sys
import pprint
import logging
from math import log, sqrt
from td.client import TDClient

# Note: reddit user says TDA API rate limit is 120 calls / minute

"""
Need to:
    1) pull down account status
    3) display account positions
    4) search for options that meet TOMIC criteria
    10) add in days since underlying last hit short leg strike
    12) do something with IV
    17) set trade critera (account size, max acceptable loss)
    19) add beta for each symbol
    20) add a sheet for fundamentals
    21) check assumption: long open interest more important. may not be the case. get avg or keep short??
"""

# create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


pp = pprint.PrettyPrinter(indent=4)


