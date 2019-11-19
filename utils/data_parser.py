__author__ = "Tao Zhang"
__copyright__ = "Copyright 2019, The VIX short Strategy"
__email__ = "uncczhangtao@yahoo.com"
from utils import date_utils
import numpy as np
import logging
import six
import pandas as pd

class YahooParser(object):
    """Yahoo Finance Data Parse Wapper Class，Decorated by DataParseWrap"""

    def __init__(self, data):
        """
        :param data: Yahoo Finance API returns pandas dataframe directly,

        """
        # index is date
        self.df = data
        columns = ['close', 'high', 'low','open','volume','date','date_week']
        if data is not None:
            # Convert date columns from string to datetime
            if isinstance(data['date'].iloc[0], six.string_types):
                self.df['dates'] = self.df['date'].apply(lambda x: date_utils.date_str_to_int(str(x)))
                self.df['date_week'] = self.df['date'].apply(lambda x: date_utils.week_of_date(str(x)))
                self.df = date_utils.pd_str_col_to_datetime(data, 'date')

                self.df = self.df.set_index('date')
                self.df['close'] = self.df['close'].astype(float)
                self.df['high'] = self.df['high'].astype(float)
                self.df['low'] = self.df['low'].astype(float)
                self.df['open'] = self.df['open'].astype(float)
                self.df['volume'] = self.df['volume'].astype(np.int64)
                self.df = self.df.rename(columns={'ticker':'symbol', 'dates':'date'})
                self.df = self.df[columns]
