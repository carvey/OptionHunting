import logging
import optparse
from utils import get_param
from openpyxl import Workbook
from openpyxl.styles import  Alignment, Font
from account import TDAuth, Watchlist
from options import VertSpread
from datetime import datetime

parser = optparse.OptionParser("usage: %prog [-t]")
parser.add_option('-t', "--test", action="store_true", dest="test", default=False)
options, args = parser.parse_args()

# create logger
logger = logging.getLogger("excel")
logger.setLevel(logging.INFO)

ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)


class ExcelFormatter:

    def __init__(self, document):
        self.wkbook = Workbook()
        self.sheet = self.wkbook.active

        self.filename = "%s.xlsx" % document

        self.alignment = Alignment(horizontal="center")
        self.bold = Font(bold=True)

    def save(self):
        # apply the styles
        for header in self.sheet["1:1"]:
            header.font = self.bold

        for row in self.sheet.rows:
            for cell in row:
                cell.alignment = self.alignment

        for column in self.sheet.columns:
            bold_columns = ["% OTM", "R/R", "POP", "Score"]
            if column[0].value in bold_columns:
                for cell in column:
                    cell.font = self.bold

        self.wkbook.save(filename=self.filename)

    def write(self, data: list):
        self.sheet.append(data)


td_client = TDAuth().td_client

# this must be pulling from real account and not paper traded?
if options.test:
    watchlist = Watchlist(td_client, get_param('test watchlist'))
else:
    watchlist = Watchlist(td_client, get_param('watchlist'))


# need to add searching/filtering from this level. Not buried in the classes
# list of dicts (each item is an instrument), where each key is a date and values are lists of VerticalSpreads
instrument_spreads = watchlist.analyze_strategy(VertSpread)

dt = datetime.strftime(datetime.now(), "%d %b %Y %I-%M-%S")
filename = "Option Hunter %s" % dt
sheet = ExcelFormatter(filename)
sheet.write(VertSpread.print_fields)

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
                details = vert_spread.details()
                sheet.write(details)

                count += 1

    logger.info("Wrote %s %s spreads to %s.xlsx" % (count, symbol, filename))

sheet.save()


