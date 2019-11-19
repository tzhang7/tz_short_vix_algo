__author__ = "Tao Zhang"
__copyright__ = "Copyright 2019, The VIX short Strategy"
__email__ = "uncczhangtao@yahoo.com"

import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(str(__file__))), os.path.pardir))
DATA_DIR = os.path.join(ROOT_DIR, 'data')

# if env.LOAD_MODE_LOCAL is Ture, it will always read it form local first
LOAD_MODE_LOCAL = True

class DataConfig(object):

    @classmethod
    def look_up_data_path(cls, symbol):
        return os.path.join(ROOT_DIR, 'data/{0}.csv'.format(str.upper(symbol)))