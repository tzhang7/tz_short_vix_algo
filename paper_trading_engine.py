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
from ib.ext.Contract import Contract
from ib.ext.Order import Order
from ib.opt import Connection, message

pd.set_option('display.max_columns', None)
pd.set_option('expand_frame_repr', False)


def error_handler(msg):
    print("Server Error:", msg)


def server_handler(msg):
    print("Server Msg:", msg.typeName, "-", msg)


def create_contract(symbol, sec_type, exch, prim_exch, curr):
    contract = Contract()
    contract.m_symbol = symbol
    contract.m_secType = sec_type
    contract.m_exchange = exch
    contract.m_primaryExch = prim_exch
    contract.m_currency = curr
    return contract


def create_order(order_type, quantity, action):
    order = Order()
    order.m_orderType = order_type
    order.m_totalQuantity = quantity
    order.m_action = action
    return order


class IBTradeEngine(object):

    def __init__(self,
                 user,
                 vix_spot_ticker='VIY00',
                 month1_ticker='VIG20',
                 month2_ticker='VIH20',
                 trade_ticker='TVIX',
                 intraday_window=30,
                 buffer_size=2):
        """

        :param vix_spot_ticker:
        :param month1_ticker:
        :param month2_ticker:
        :param trade_ticker:
        :param intraday_window: monitor signal every 30 mins
        """
        self.user = user
        self.vix_spot_ticker = vix_spot_ticker
        self.month1_ticker = month1_ticker
        self.month2_ticker = month2_ticker
        self.yahoo_data_loader = YahooDataLoader()
        self.trade_date = datetime.datetime.today()
        self.market_open_hour = datetime.time(9, 30, 0)
        self.market_close_hour = datetime.time(23, 0, 0)

        self.trade_strategy_engine = ShortVixAlgo()
        self.trade_ticker = trade_ticker
        self.intraday_window = intraday_window
        self.buffer_size = buffer_size
        self.hold_flag = False
        self.hold_index = 0
        self.setup_coef = 0.3
        self.order_id = 123
        # Establish connection to TWS.
        self.tws_conn = Connection.create(port=7497, clientId=999)
        self.tws_conn.connect()

        # Assign error handling function.
        self.tws_conn.register(error_handler, 'Error')

        # Assign server messages handling function.
        self.tws_conn.registerAll(server_handler)
        # Create TVIX contract and send order
        self.tvix_contract = create_contract(trade_ticker, 'STK', 'SMART', 'SMART', 'USD')

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
        logger.info("Market data loaded, takes {0} seconds".format(end - start))

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
        Save user logs and clear, keep the last line
        :return:
        """
        user = self.user
        if not user.trade_log_tbl.empty:
            user.trade_log_tbl.to_csv(
                env.OUTPUT_DIR + '/{0}_trade_log_{1}.csv'.format(user.name, datetime.date.today()))

            last_line = user.trade_log_tbl.tail(1)
            user.trade_log_tbl = PandasUtils.df_empty(user.trade_log_schema)
            user.trade_log_tbl = user.trade_log_tbl.append(last_line)
            logger.info("{0}'s logs saved.".format(user.name))

    def rebalance_action(self, close_position, open_position):
        tvix_order = create_order('MKT', close_position, 'BUY')
        self.tws_conn.placeOrder(self.order_id, self.tvix_contract, tvix_order)
        self.order_id += 1

        tvix_order = create_order('MKT', open_position, 'SELL')
        self.tws_conn.placeOrder(self.order_id, self.tvix_contract, tvix_order)
        self.order_id += 1

    def get_backtesting_data(self):
        trade_dates = ['2019-12-10', '2019-12-11']
        dfs = []
        for d in trade_dates:
            df = pd.read_csv()

    def backtesting(self):
        user = self.user
        t = 0

        back_test_data = self.get_backtesting_data()
        wa_ratio = self.calc_signal()
        # Calc position coef
        if wa_ratio < user.deep_contango_coef:
            position_coef = user.deep_contango_setup_coef
        elif wa_ratio < user.enter_coef:
            position_coef = user.setup_coef
        else:
            position_coef = 0

        signal = position_coef != 0

        if signal:  # now signal is open
            if user.trade_log_tbl.empty:  # it's first trading
                log = 'Open'
                capital = user.capital
                position = capital * position_coef / self.trade_market_px
                unrealized_pnl = 0
                realized_pnl = 0
                pnl = 0
                # TODO COMMENT OUT IB API
                # tvix_order = create_order('MKT', position, 'SELL')
                # self.tws_conn.placeOrder(self.order_id, self.tvix_contract, tvix_order)
                # self.order_id += 1
            else:
                previous_signal = user.trade_log_tbl['signal'].iloc[t - 1]
                pre_trade_px = user.trade_log_tbl['market_px'].iloc[t - 1]
                pre_position = user.trade_log_tbl['position'].iloc[t - 1]
                previous_capital = user.trade_log_tbl['capital'].iloc[t - 1]
                pnl = (self.trade_market_px - pre_trade_px) * pre_position  # Pnl always now - previous
                if previous_signal:  # Previous signal is Open

                    # If today's pnl is negative and position is not hold, hold the position
                    if pnl < self.trade_market_px * self.buffer_size and not self.hold_flag:
                        self.hold_flag = True
                        self.hold_index = t

                    # calculate the unrealized pnl
                    if self.hold_index > 0:
                        log = 'hold'  # no action
                        unrealized_pnl = user.trade_log_tbl['pnl'][self.hold_index:t + 1].sum()
                        realized_pnl = 0
                    else:
                        # SELL first then Buy
                        log = 'rebalance'
                        unrealized_pnl = 0
                        realized_pnl = pnl
                        capital = previous_capital + realized_pnl
                        position = capital / self.trade_market_px
                        # TODO COMMENT OUT IB API
                        # self.rebalance_action(close_position=pre_position, open_position=position)
                        self.hold_index = 0

                    # Hold until realized_pnl >0
                    if self.hold_flag and unrealized_pnl > self.trade_market_px * self.buffer_size:
                        log = "Hold until unrealized_pnl > 0"
                        realized_pnl = unrealized_pnl
                        unrealized_pnl = 0
                        capital = previous_capital + realized_pnl
                        position = capital / self.trade_market_px
                        # TODO COMMENT OUT IB API
                        # self.rebalance_action(close_position=pre_position, open_position=position)
                        self.hold_flag = False
                        self.hold_index = 0
                else:  # Previous signal is Close, now signal is Open
                    log = 'Open'
                    position = previous_capital * self.setup_coef / self.trade_market_px
                    unrealized_pnl = 0
                    realized_pnl = 0
                    pnl = 0
                    # TODO COMMENT OUT IB API
                    # tvix_order = create_order('MKT', position, 'SELL')
                    # self.tws_conn.placeOrder(self.order_id, self.tvix_contract, tvix_order)
                    # self.order_id += 1
                    self.hold_flag = False
                    self.hold_index = 0
        else:  # now signal is close
            if user.trade_log_tbl.empty:  # it's first trading
                log = 'Close'
                capital = user.capital
                position = 0
                unrealized_pnl = 0
                realized_pnl = 0
                pnl = 0
            else:
                previous_signal = user.trade_log_tbl['signal'].iloc[t - 1]
                pre_trade_px = float(user.trade_log_tbl['market_px'].iloc[t - 1])
                pre_unrealized_pnl = user.trade_log_tbl['unrealized_pnl'].iloc[t - 1]
                pre_position = user.trade_log_tbl['position'].iloc[t - 1]
                previous_capital = user.trade_log_tbl['capital'].iloc[t - 1]
                pnl = (self.trade_market_px - pre_trade_px) * pre_position
                if previous_signal:  # if previous is open, now is close
                    log = 'Close'
                    position = 0
                    unrealized_pnl = 0
                    realized_pnl = pre_unrealized_pnl + pnl
                    capital = previous_capital + realized_pnl
                    # TODO COMMENT OUT IB API
                    # tvix_order = create_order('MKT', pre_position, 'BUY')
                    # self.tws_conn.placeOrder(self.order_id, self.tvix_contract, tvix_order)
                    # self.order_id += 1
                else:  # if previous is close, now is close
                    log = 'Close'
                    position = 0
                    unrealized_pnl = 0
                    realized_pnl = 0
                    capital = previous_capital + realized_pnl

        user.trade_log_tbl = PandasUtils.addRow(user.trade_log_tbl,
                                                [trade_time.strftime("%d.%b %Y %H:%M:%S"), user.name,
                                                 self.vix_month1_px,
                                                 self.vix_month2_px,
                                                 self.vix_spot_px, round(wa_ratio, 4),
                                                 self.trade_market_px,
                                                 signal,
                                                 position,
                                                 unrealized_pnl,
                                                 realized_pnl,
                                                 pnl,
                                                 capital,
                                                 log])
        t += 1
        print(user.trade_log_tbl)
        logger.info("Sleeping for {0} seconds...".format(self.intraday_window))
        time.sleep(self.intraday_window)

    def start_trading(self):
        """
        start trading: 1. Monitor signal 2. send notification to registered users
        :return:
        """
        user = self.user
        t = 0
        while True:
            trade_time = datetime.datetime.now()

            if self.market_open_hour <= trade_time.time() <= self.market_close_hour:
                # Only monitor the signal during market hours
                logger.info("*************** Market Open ***************")
                self.get_market_data()
                wa_ratio = self.calc_signal()
                # Calc position coef
                if wa_ratio < user.deep_contango_coef:
                    position_coef = user.deep_contango_setup_coef
                elif wa_ratio < user.enter_coef:
                    position_coef = user.setup_coef
                else:
                    position_coef = 0

                signal = position_coef != 0

                if signal:  # now signal is open
                    if user.trade_log_tbl.empty:  # it's first trading
                        log = 'Open'
                        capital = user.capital
                        position = capital * position_coef / self.trade_market_px
                        unrealized_pnl = 0
                        realized_pnl = 0
                        pnl = 0
                        # TODO COMMENT OUT IB API
                        # tvix_order = create_order('MKT', position, 'SELL')
                        # self.tws_conn.placeOrder(self.order_id, self.tvix_contract, tvix_order)
                        # self.order_id += 1
                    else:
                        previous_signal = user.trade_log_tbl['signal'].iloc[t - 1]
                        pre_trade_px = user.trade_log_tbl['market_px'].iloc[t - 1]
                        pre_position = user.trade_log_tbl['position'].iloc[t - 1]
                        previous_capital = user.trade_log_tbl['capital'].iloc[t - 1]
                        pnl = (self.trade_market_px - pre_trade_px) * pre_position  # Pnl always now - previous
                        if previous_signal:  # Previous signal is Open

                            # If today's pnl is negative and position is not hold, hold the position
                            if pnl < self.trade_market_px * self.buffer_size and not self.hold_flag:
                                self.hold_flag = True
                                self.hold_index = t

                            # calculate the unrealized pnl
                            if self.hold_index > 0:
                                log = 'hold'  # no action
                                unrealized_pnl = user.trade_log_tbl['pnl'][self.hold_index:t + 1].sum()
                                realized_pnl = 0
                            else:
                                # SELL first then Buy
                                log = 'rebalance'
                                unrealized_pnl = 0
                                realized_pnl = pnl
                                capital = previous_capital + realized_pnl
                                position = capital / self.trade_market_px
                                # TODO COMMENT OUT IB API
                                # self.rebalance_action(close_position=pre_position, open_position=position)
                                self.hold_index = 0

                            # Hold until realized_pnl >0
                            if self.hold_flag and unrealized_pnl > self.trade_market_px * self.buffer_size:
                                log = "Hold until unrealized_pnl > 0"
                                realized_pnl = unrealized_pnl
                                unrealized_pnl = 0
                                capital = previous_capital + realized_pnl
                                position = capital / self.trade_market_px
                                # TODO COMMENT OUT IB API
                                # self.rebalance_action(close_position=pre_position, open_position=position)
                                self.hold_flag = False
                                self.hold_index = 0
                        else:  # Previous signal is Close, now signal is Open
                            log = 'Open'
                            position = previous_capital * self.setup_coef / self.trade_market_px
                            unrealized_pnl = 0
                            realized_pnl = 0
                            pnl = 0
                            # TODO COMMENT OUT IB API
                            # tvix_order = create_order('MKT', position, 'SELL')
                            # self.tws_conn.placeOrder(self.order_id, self.tvix_contract, tvix_order)
                            # self.order_id += 1
                            self.hold_flag = False
                            self.hold_index = 0
                else:  # now signal is close
                    if user.trade_log_tbl.empty:  # it's first trading
                        log = 'Close'
                        capital = user.capital
                        position = 0
                        unrealized_pnl = 0
                        realized_pnl = 0
                        pnl = 0
                    else:
                        previous_signal = user.trade_log_tbl['signal'].iloc[t - 1]
                        pre_trade_px = float(user.trade_log_tbl['market_px'].iloc[t - 1])
                        pre_unrealized_pnl = user.trade_log_tbl['unrealized_pnl'].iloc[t - 1]
                        pre_position = user.trade_log_tbl['position'].iloc[t - 1]
                        previous_capital = user.trade_log_tbl['capital'].iloc[t - 1]
                        pnl = (self.trade_market_px - pre_trade_px) * pre_position
                        if previous_signal:  # if previous is open, now is close
                            log = 'Close'
                            position = 0
                            unrealized_pnl = 0
                            realized_pnl = pre_unrealized_pnl + pnl
                            capital = previous_capital + realized_pnl
                            # TODO COMMENT OUT IB API
                            # tvix_order = create_order('MKT', pre_position, 'BUY')
                            # self.tws_conn.placeOrder(self.order_id, self.tvix_contract, tvix_order)
                            # self.order_id += 1
                        else:  # if previous is close, now is close
                            log = 'Close'
                            position = 0
                            unrealized_pnl = 0
                            realized_pnl = 0
                            capital = previous_capital + realized_pnl

                user.trade_log_tbl = PandasUtils.addRow(user.trade_log_tbl,
                                                        [trade_time.strftime("%d.%b %Y %H:%M:%S"), user.name,
                                                         self.vix_month1_px,
                                                         self.vix_month2_px,
                                                         self.vix_spot_px, round(wa_ratio, 4),
                                                         self.trade_market_px,
                                                         signal,
                                                         position,
                                                         unrealized_pnl,
                                                         realized_pnl,
                                                         pnl,
                                                         capital,
                                                         log])
                t += 1
                print(user.trade_log_tbl)
                logger.info("Sleeping for {0} seconds...".format(self.intraday_window))
                time.sleep(self.intraday_window)

            else:
                logger.info("Market closed, please wait ...")
                # save user logs and clear the logs
                self.save_user_logs_and_clear()

                logger.info("Sleeping for {0} seconds...".format(self.intraday_window))
                time.sleep(self.intraday_window)


if __name__ == '__main__':
    user = User('tao', 'tzshortvix@gmail.com')
    runner = IBTradeEngine(user)
    runner.start_trading()
