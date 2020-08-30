"""
This will need a few componets to work:
    1) logic to use the previously written logic to analyze a watchlist 
    2) criteria to select trades
    3) interface to TDA API to make orders
    4) order vert spread
    5) automatically calculate and place -50% stop losses and +70% limit buy orders 
    6) set up fake TDA API to receive the requests
    7) have fake TDA API log trade information to sqlite 
    7.5) have fake api query (streaming possible) the real TDA API for price updates
    8) write logic to query sqlite for trade performance
    9) create "fake" portfolio to track auto trader performance

    Scratch all that. Can just:
    1) write trading logic
    2) have factory return 
"""
