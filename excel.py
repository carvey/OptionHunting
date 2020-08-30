from openpyxl import Workbook
from account import TDAuth, Watchlist
from options import VertSpread
from datetime import datetime


class ExcelFormatter:

    def __init__(self, document):
        self.wkbook = Workbook()
        self.sheet = self.wkbook.active

        self.filename = "%s.xlsx" % document

    def save(self):
        self.wkbook.save(filename=self.filename)

    def write(self, data: list, save=True):
        self.sheet.append(data)
        if save:
            self.save()


td_client = TDAuth().td_client

# this must be pulling from real account and not paper traded?
watchlist = Watchlist(td_client, 'Option Scanning')

# need to add searching/filtering from this level. Not buried in the classes
# list of dicts (each item is an instrument), where each key is a date and values are lists of VerticalSpreads
instrument_spreads = watchlist.analyze_strategy(VertSpread)

dt = str(datetime.now()).split('.')[0]
log = ExcelFormatter("log %s" % dt)
log.write(VertSpread.print_fields)

for instrument in instrument_spreads:
    for exp_date, spreads in instrument.items():
        for vert_spread in spreads:
            details = vert_spread.details()
            log.write(details, False)

log.save()
