__author__ = "Tao Zhang"
__copyright__ = "Copyright 2019, The VIX short Strategy"
__email__ = "uncczhangtao@yahoo.com"

from market.market_data_feeder import YahooDataLoader
from market import market_data_crawer
from short_vix_algo import ShortVixAlgo
from config.user import User
from notification.email_notification import EmailNotification
from utils.pandas_utils import PandasUtils
from config import env
from config.env import logger
import datetime
import time
import pandas as pd

pd.set_option('display.max_columns', None)
pd.set_option('expand_frame_repr', False)


class RealTradeEngine(object):

    def __init__(self,
                 users,
                 vix_spot_ticker='VIY00',
                 month1_ticker='VIZ19',
                 month2_ticker='VIF20',
                 trade_ticker='TVIX',
                 intraday_window=300):
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
        # self.ts = TimeSeries(key='65DFM5X22B49MNZ3', output_format='pandas')

    def get_market_data(self):
        """
        Get all required ticker's market data
        :return:
        """
        logger.info("Loading market data...")
        start = datetime.datetime.now()
        self.vix_spot_px = market_data_crawer.get_barchart_real_time_data(self.vix_spot_ticker)
        self.vix_month1_px = market_data_crawer.get_barchart_real_time_data(self.month1_ticker)
        self.vix_month2_px = market_data_crawer.get_barchart_real_time_data(self.month2_ticker)
        self.trade_market_px = market_data_crawer.get_barchart_real_time_data(self.trade_ticker)
        end = datetime.datetime.now()
        logger.info("Market data loaded, takes {0} seconds".format( end - start))


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

    def save_user_logs_and_clear(self):
        """
        Save user logs and clear
        :return:
        """
        for user in self.users:
            if not user.trade_log_tbl.empty:
                user.trade_log_tbl.to_csv(env.OUTPUT_DIR + '/{0}_trade_log_{1}.csv'.format(user.name, datetime.date.today()))

                body = EmailNotification.covert_df_to_html(user.trade_log_tbl)
                subject = '***Short VIX Signal EOD Summary***'
                EmailNotification.send_email(user.email, subject, body)

                user.trade_log_tbl = PandasUtils.df_empty(user.trade_log_schema)
                logger.info("{0}'s logs saved.".format(user.name))

    def start_trading(self):
        """
        start trading: 1. Monitor signal 2. send notification to registered users
        :return:
        """
        # calc enter signal
        while True:
            trade_time = datetime.datetime.now()

            if self.market_open_hour <= trade_time.time() <= self.market_close_hour:
                # Only monitor the signal during market hours
                logger.info("*************** Market Open ***************")
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
                        if user.open_email:
                            sent_email = True
                            user.open_email = False
                        else:
                            sent_email = False

                    else:
                        position = 0
                        subject = "Short VIX Close signal"
                        log = 'Close'
                        sent_email = True  # close signal always send email with high priority

                    user.trade_log_tbl = PandasUtils.addRow(user.trade_log_tbl,
                                                            [trade_time.strftime("%d.%b %Y %H:%M:%S"), user.name, self.vix_month1_px,
                                                             self.vix_month2_px,
                                                             self.vix_spot_px, round(wa_ratio,4), self.trade_market_px, capital,
                                                             position, log, sent_email])
                    logger.info("-----------------------------------------------------------------------------------")
                    if user.only_show_signal:
                        signal_tbl = user.trade_log_tbl[
                            ['time', 'user', 'vix_mth1', 'vix_mth2', 'vix_spot', 'wa_ratio', 'market_px', 'log']]
                        if user.print_log:
                            print(signal_tbl)

                        if sent_email:
                            body = EmailNotification.covert_df_to_html(signal_tbl)
                            EmailNotification.send_email(recipient_email, subject, body)
                    else:
                        logger.info(user.trade_log_tbl)
            else:
                logger.info("Market closed, please wait ...")
                # save user logs and clear the logs
                self.save_user_logs_and_clear()

            logger.info("Sleeping for {0} seconds...".format(self.intraday_window))
            time.sleep(self.intraday_window)


if __name__ == '__main__':
    user1 = User('tao', 'tzshortvix@gmail.com')
    user2 = User('ruicheng', 'ruichengma2@gmail.com', print_log=False)
    users = [user1, user2]
    runner = RealTradeEngine(users)
    runner.start_trading()
