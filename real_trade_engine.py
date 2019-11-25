__author__ = "Tao Zhang"
__copyright__ = "Copyright 2019, The VIX short Strategy"
__email__ = "uncczhangtao@yahoo.com"

from market.market_data_feeder import YahooDataLoader
from market import market_data_crawer
from short_vix_algo import ShortVixAlgo
from config import user_config
from notification import email_notification
from alpha_vantage.timeseries import TimeSeries
import datetime
import time
import pandas as pd


class RealTradeEngine(object):

    def __init__(self, setup_coef=0.3,
                 deep_contango_setup_coef=0.4,
                 enter_coef=0.95,
                 deep_contango_coef=0.90,
                 vix_spot_ticker='^VIX',
                 month1_ticker='VIZ19',
                 month2_ticker='VIF20',
                 trade_ticker='TVIX',
                 intraday_window='1800'):
        """

        :param setup_coef:
        :param deep_contango_setup_coef:
        :param enter_coef:
        :param deep_contango_coef:
        :param vix_spot_ticker:
        :param month1_ticker:
        :param month2_ticker:
        :param trade_ticker:
        :param intraday_window: monitor signal every 30 mins
        """
        self.setup_coef = setup_coef
        self.deep_contango_setup_coef = deep_contango_setup_coef
        self.enter_coef = enter_coef
        self.deep_contango_coef = deep_contango_coef
        self.vix_spot_ticker = vix_spot_ticker
        self.month1_ticker = month1_ticker
        self.month2_ticker = month2_ticker
        self.yahoo_data_loader = YahooDataLoader()
        self.trade_date = datetime.datetime.today()
        # TODO check if trade date is in market hours
        self.trade_strategy_engine = ShortVixAlgo()
        self.trade_ticker = trade_ticker
        self.intraday_window = intraday_window
        self.trade_log = pd.DataFrame(
            columns={'time', 'future_mth1', 'future_mth2', 'vix_spot', 'self.wa_ratio', 'market_px', 'capital',
                     'position', 'log'})

        self.ts = TimeSeries(key='65DFM5X22B49MNZ3', output_format='pandas')

    def monitor_signal(self):
        """
        Calc Enter and Exit Signal Based on T+0 data
        :return: sginal, position_coef
        """

        self.vix_spot_px = self._get_intraday_data(self.vix_spot_ticker)
        self.vix_month1_px = market_data_crawer.get_future_real_time_data(self.month1_ticker)
        self.vix_month2_px = market_data_crawer.get_future_real_time_data(self.month2_ticker)

        # calc ratio1 and ratio2
        ratio1 = self.vix_spot_px / self.vix_month1_px
        ratio2 = self.vix_month1_px / self.vix_month2_px

        # calc TTM and period date
        current_expire = self.trade_strategy_engine.find_future_expire_date(self.trade_date,
                                                                            self.trade_strategy_engine.expire_date_mapping,
                                                                            0)
        previous_expire = self.trade_strategy_engine.find_future_expire_date(self.trade_date,
                                                                             self.trade_strategy_engine.expire_date_mapping,
                                                                             -1)
        next_expire = self.trade_strategy_engine.find_future_expire_date(self.trade_date,
                                                                         self.trade_strategy_engine.expire_date_mapping,
                                                                         1)

        ttm = current_expire - self.trade_date if current_expire > self.trade_date else next_expire - self.trade_date
        period = current_expire - previous_expire if current_expire >= self.trade_date else next_expire - current_expire

        # calc weighted average
        self.wa_ratio = ttm / period * ratio1 + (1 - ttm / period) * ratio2

        # calc signal
        if self.wa_ratio < self.deep_contango_coef:
            return True, self.deep_contango_setup_coef,
        elif self.wa_ratio < self.enter_coef:
            return True, self.setup_coef
        else:
            return False, 0

    def _get_intraday_data(self, ticker):

        data, meta_data = self.ts.get_intraday(ticker, interval='30min')
        return data.loc[meta_data['3. Last Refreshed']]['1. open'].iloc[0]

    def start_trading(self):
        """
        start trading: 1. Monitor signal 2. send notification to registered users
        :return:
        """
        # calc enter signal
        while True:
            signal, position_coef = self.monitor_signal()
            market_px = self._get_intraday_data(self.trade_ticker)
            trade_time = datetime.datetime.now()
            # self.trade_log = self.trade_log.append([])

            for user_name, user_setting in user_config.users.iteriterms():
                if signal:
                    # calc the position
                    position = -user_setting['capital'] / market_px
                    subject = "Short VIX Open signal"
                    body = ''

            time.sleep(self.intraday_window)


if __name__ == '__main__':
    runner = RealTradeEngine()
    runner.start_trading()
