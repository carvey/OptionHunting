import optparse
from utils import get_param, start_logger, define_parser
from account import get_watchlist
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font
from options import VertSpread, PutCreditSpread, CallCreditSpread
from datetime import datetime

logger = start_logger("excel")

options, args = define_parser()

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

    def write_spreads(self, instrument_spreads):
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
                        self.write(details)

                        count += 1

            logger.info("Wrote %s %s spreads to %s.xlsx" % (count, symbol, filename))

        self.save()

# initialize TDA connection and get the appropriate watchlist
watchlist = get_watchlist(options)

dt = datetime.strftime(datetime.now(), "%d %b %Y %I-%M-%S")
filename = "Option Hunter %s" % dt
sheet = ExcelFormatter(filename)

# write the column headers
sheet.write(VertSpread.field_names)

# need to add searching/filtering from this level. Not buried in the classes
# list of dicts (each item is an instrument), where each key is a date and values are lists of VerticalSpreads
instrument_spreads = watchlist.analyze_strategy()
sheet.write_spreads(instrument_spreads)
