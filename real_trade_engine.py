__author__ = "Tao Zhang"
__copyright__ = "Copyright 2019, The VIX short Strategy"
__email__ = "uncczhangtao@yahoo.com"

from market.market_data_feeder import YahooDataLoader
from market import market_data_crawer
from short_vix_algo import ShortVixAlgo
from config.user import User
from notification.email_notification import EmailNotification
from utils.pandas_utils import PandasUtils
from alpha_vantage.timeseries import TimeSeries
import datetime
import time


class RealTradeEngine(object):

    def __init__(self,
                 users,
                 vix_spot_ticker='^VIX',
                 month1_ticker='VIZ19',
                 month2_ticker='VIF20',
                 trade_ticker='TVIX',
                 intraday_window='1800'):
        """

        :param vix_spot_ticker:
        :param month1_ticker:
        :param month2_ticker:
        :param trade_ticker:
        :param intraday_window: monitor signal every 30 mins
        """
        self.users = users
        self.vix_spot_ticker = vix_spot_ticker
        self.month1_ticker = month1_ticker
        self.month2_ticker = month2_ticker
        self.yahoo_data_loader = YahooDataLoader()
        self.trade_date = datetime.datetime.today()
        self.market_open_hour = datetime.time(8)
        self.market_close_hour = datetime.time(15, 45, 0)
        self.trade_strategy_engine = ShortVixAlgo()
        self.trade_ticker = trade_ticker
        self.intraday_window = intraday_window
        self.open_email = True
        self.ts = TimeSeries(key='65DFM5X22B49MNZ3', output_format='pandas')

    def get_market_data(self):
        """
        Get all required ticker's market data
        :return:
        """
        self.vix_spot_px = self._get_intraday_data(self.vix_spot_ticker)
        self.vix_month1_px = market_data_crawer.get_future_real_time_data(self.month1_ticker)
        self.vix_month2_px = market_data_crawer.get_future_real_time_data(self.month2_ticker)
        self.trade_market_px = self._get_intraday_data(self.trade_ticker)

    def calc_signal(self):
        """
        Calc Enter and Exit Signal Based on T+0 data
        :return: sginal, position_coef
        """
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
        wa_ratio = ttm / period * ratio1 + (1 - ttm / period) * ratio2

        return wa_ratio

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
            trade_time = datetime.datetime.now()

            if trade_time.time() >= self.market_open_hour and trade_time.time() <= self.market_close_hour:
                # Only monitoring the signal during market hours 
                self.get_market_data()
                wa_ratio = self.calc_signal()

                for user in self.users:
                    capital = user.capital
                    recipient_email = user.email

                    if wa_ratio < user.deep_contango_coef:
                        position_coef = user.deep_contango_setup_coef
                    elif wa_ratio < user.enter_coef:
                        position_coef = user.setup_coef
                    else:
                        position_coef = 0

                    signal = position_coef != 0

                    if signal:
                        # calc the position
                        position = -capital * position_coef / self.trade_market_px
                        log = 'Open'
                        subject = "Short VIX Open signal"
                        if self.open_email:
                            sent_email = True
                        else:
                            sent_email = False
                            self.open_email = False
                    else:
                        position = 0
                        subject = "Short VIX Open signal"
                        log = 'Close'
                        sent_email = True

                    user.trade_log_tbl = PandasUtils.addRow(user.trade_log_tbl,
                                                            [trade_time, user.name, self.vix_month1_px,
                                                             self.vix_month2_px,
                                                             self.vix_spot_px, wa_ratio, self.trade_market_px, capital,
                                                             position, log, sent_email])
                    if sent_email:
                        body = EmailNotification.covert_df_to_html(user.trade_log_tbl)
                        EmailNotification.send_email(recipient_email, subject, body)

            print("Sleeping for 30 mins... Zzzzz")
            time.sleep(self.intraday_window)


if __name__ == '__main__':
    user1 = User('tao', 'tzshortvix@gmail.com', capital=2000)
    user2 = User('ruicheng', 'tzshortvix@gmail.com', capital=2000)

    runner = RealTradeEngine([user1, user2])
    runner.start_trading()
