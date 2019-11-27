# -*- coding: utf-8 -*-
# @Time    : 9/21/19 01:00
# @Author  : Tao Zhang

from config import env
from utils.data_parser import YahooParser
from utils import date_utils
from yahoo_fin import stock_info as si
import pandas as pd
import os
import logging
import ondemand


class YahooDataLoader(object):

    def __init__(self):
        self._action_id = int(date_utils.time_seconds())
        self.data_parser_cls = YahooParser

    def kline(self, ticker, n_folds=2, start=None, end=None):
        """
        Load historical data from local or Yahoo Finance
        :param n_folds: the years you want to look back
        :param start: start date as string, e.g. '2019-01-01'
        :param end: end date as string, e.g. '2019-01-01', by default, it's current date
        :return: returns pandas dataframe and save, by default it will return 2 years data.
        """
        # by default it will always find the data from local, but the data may not be the latest
        # when overwrite flag is True, it will force read it from yahoo and overwrite the local data
        kf_dl = None
        if not end:
            end = date_utils.current_str_date()

        if not start and n_folds > 0:
            start = date_utils.begin_date(n_folds * 365, end)

        if not env.LOAD_MODE_LOCAL:
            response = self._yahoo_get_data(ticker, start, end)
        else:
            # Find it from local first, else read it from local
            for root, dirs, files in os.walk(env.DATA_DIR):
                if str.upper(ticker) + '.csv' in files:
                    logging.info('ticker Found in Local')
                    response = pd.read_csv(os.path.join(env.DATA_DIR, '{0}.csv'.format(str.upper(ticker))))
                else:
                    # Even overwrite flag is True, it may not have data in local, fetch it from yahoo
                    response = self._yahoo_get_data(ticker, start, end)

        if response is not None and env.LOAD_MODE_LOCAL:
            result = self.data_parser_cls(response).df
            if result is not None:
                return result
        return response

    def _yahoo_get_data(self, ticker, start, end):
        try:
            print(
                "Downloading from yahoo Finance..."
                "Please make sure you have internet connected!")
            response = si.get_data(ticker, start, end)
            if not response.empty:
                response.to_csv(os.path.join(env.DATA_DIR, '{0}.csv'.format(str.upper(ticker))))

        except Exception as ex:
            logging.error("error in getting historical data from Yahoo Finance!")
            logging.error(str(ex))

        return response

    def get_live_price(self, ticker, save=True):
        try:
            rep = si.get_live_price(ticker)
            print(rep)
        except Exception as ex:
            logging.error("error in getting real time price from Yahoo Finance!")
            logging.error(str(ex))

