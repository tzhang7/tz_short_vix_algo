__author__ = "Tao Zhang"
__copyright__ = "Copyright 2019, The VIX short Strategy"
__email__ = "uncczhangtao@yahoo.com"

import os
import logging
import tempfile
import datetime

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(str(__file__))), os.path.pardir))
DATA_DIR = os.path.join(ROOT_DIR, 'data')
OUTPUT_DIR = os.path.join(ROOT_DIR, 'output')
logLocation = tempfile.mktemp(suffix='.log', prefix='vix_trade_algo_app' + str(datetime.date.today()) + '_')

# if env.LOAD_MODE_LOCAL is Ture, it will always read it form local first
LOAD_MODE_LOCAL = True


def get_logger():
    # set up logging to file
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s -%(levelname)s: - %(message)s',
        datefmt='%Y-%m-%d %H:%m:%S'
    )

    # Logger will be saved in file
    fh = logging.FileHandler(logLocation)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)

    # Logger will be printed in screen
    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)

    logger.addHandler(ch)
    logger.addHandler(fh)

    return logger


logger = get_logger()


class DataConfig(object):

    @classmethod
    def look_up_data_path(cls, symbol):
        return os.path.join(ROOT_DIR, 'data/{0}.csv'.format(str.upper(symbol)))
