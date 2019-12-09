__author__ = "Tao Zhang"
__copyright__ = "Copyright 2019, The VIX short Strategy"
__email__ = "uncczhangtao@yahoo.com"

import os
import logging

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(str(__file__))), os.path.pardir))
DATA_DIR = os.path.join(ROOT_DIR, 'data')
OUTPUT_DIR = os.path.join(ROOT_DIR,'output')

# if env.LOAD_MODE_LOCAL is Ture, it will always read it form local first
LOAD_MODE_LOCAL = True

def get_logger():
    # set up logging to file
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                        datefmt='%m-%d %H:%M',
                        filename=OUTPUT_DIR +'app.log',
                        filemode='w')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)
    return logging

logger = get_logger()

class DataConfig(object):

    @classmethod
    def look_up_data_path(cls, symbol):
        return os.path.join(ROOT_DIR, 'data/{0}.csv'.format(str.upper(symbol)))