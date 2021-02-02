import json
import logging
import optparse

def get_param(param):
    param_file = open('parameters.txt')
    data = param_file.read()
    param_file.close()

    param_data = json.loads(data)
    if param in param_data:
        return param_data[param]

def start_logger(name):
    # create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    
    return logger

def define_parser():
    parser = optparse.OptionParser("usage: %prog [-l] [-r]")
    parser.add_option('-l', "--local", action="store_true", dest="local", default=False)
    parser.add_option('-r', "--remote", action="store_true", dest="remote", default=False)
    options, args = parser.parse_args()

    if options.local and options.remote:
        parser.error("You cannot specify a local and remote watchlist.")

    if not options.local and not options.remote:
        parser.error("You must specify to use a local or remote watchlist with --local or --remote")

    return options, args
