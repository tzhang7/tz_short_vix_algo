from utils.pandas_utils import PandasUtils
from utils import date_utils
from market.market_data_feeder import YahooDataLoader
from pandas.plotting import register_matplotlib_converters
from dateutil.relativedelta import *
import matplotlib.pyplot as plt
import pandas
import os
import logging
import locale
import numpy

register_matplotlib_converters()
#locale.setlocale(locale.LC_ALL, 'en_US')


class ShortVixAlgo(object):
    """
    Short VIX Algorithm, medium trading frequency
    """

    def __init__(self,
                 setup_coef=0.3,
                 deep_contango_setup_coef=0.4,
                 enter_coef=0.95,
                 deep_contango_coef=0.90,
                 start_trading_date="2011-01-01",
                 end_trading_date=date_utils.current_str_date(),
                 ticker='TVIX',
                 benchmark_ticker='^GSPC',
                 initial_capital=10000):

        self.root = os.path.abspath(os.path.dirname(__file__))
        self.data_dir = self.root + '/data/'
        self.output_dir = self.root + '/output/'
        self.his_data_file = 'vix-funds-models-no-formulas.xlsx'
        self.cobe_future_expire_date_mapping = 'calendar.txt'
        self.setup_coef = setup_coef
        self.deep_contango_setup_coef = deep_contango_setup_coef
        self.enter_coef = enter_coef
        self.deep_contango_coef = deep_contango_coef
        self.start_trading_date = date_utils.str_to_datetime_fast(start_trading_date)
        self.end_trading_date = date_utils.str_to_datetime_fast(end_trading_date)
        self.ticker = ticker
        self.initial_capital = initial_capital
        self.yahoo_loader = YahooDataLoader()
        self.start_trading_date_str = date_utils.datetime_to_str(self.start_trading_date)
        self.benchmark_ticker = benchmark_ticker
        # load future expire date mapping
        self.expire_date_mapping = pandas.read_csv(self.data_dir + self.cobe_future_expire_date_mapping)
        self.expire_date_mapping = PandasUtils.convert_date_str_to_datetime(self.expire_date_mapping, 'expire date')
        self.expire_date_mapping['expire_month'] = self.expire_date_mapping.apply(
            lambda row: row['expire date'].strftime('%Y%m'),
            axis=1)

    def get_his_mkt_data(self, ticker):

        result = self.yahoo_loader.kline(ticker, start=self.start_trading_date_str)

        return result[['open', 'close', 'volume', 'high', 'low']].reset_index()

    def process_data(self):
        """
        Create modeling data
        :return:
        """
        # load ticker market data
        logging.info('Loading Market Data from Yahoo Finance...')
        market_data = self.get_his_mkt_data(self.ticker)

        logging.info('Loading Modeling Data...')
        # load historical futures and VIX data, and calc ratios
        vix_history = pandas.read_excel(self.data_dir + self.his_data_file)
        vix_history = vix_history[['Date', '1st mth', '2nd mth', 'VIX']]
        vix_history = vix_history.rename(columns={'Date': 'date'})
        vix_history = vix_history[
            (vix_history['date'] >= self.start_trading_date) & (vix_history['date'] <= self.end_trading_date)]

        # find the current, previous and next expire date based on the mapping
        vix_history['current_expire'] = vix_history.apply(
            lambda row: self.find_future_expire_date(row['date'], self.expire_date_mapping, 0), axis=1)
        vix_history['previous_expire'] = vix_history.apply(
            lambda row: self.find_future_expire_date(row['date'], self.expire_date_mapping, -1), axis=1)
        vix_history['next_expire'] = vix_history.apply(
            lambda row: self.find_future_expire_date(row['date'], self.expire_date_mapping, 1), axis=1)

        # find TTM and period date in order to calc weighted avg
        vix_history['TTM'] = vix_history.apply(
            lambda row: row['current_expire'] - row['date'] if row['current_expire'] >= row['date']
            else row['next_expire'] - row['date'], axis=1)

        vix_history['Period'] = vix_history.apply(
            lambda row: row['current_expire'] - row['previous_expire'] if row['current_expire'] >= row['date']
            else row['next_expire'] - row['current_expire'], axis=1)
        # calculate ratios
        vix_history['ratio1'] = vix_history['VIX'] / vix_history['1st mth']
        vix_history['ratio2'] = vix_history['1st mth'] / vix_history['2nd mth']
        vix_history['sa_ratio'] = (vix_history['ratio1'] + vix_history['ratio2']) / 2
        vix_history['wa_ratio'] = vix_history['TTM'] / vix_history['Period'] * vix_history['ratio1'] + (
                1 - vix_history['TTM'] / vix_history['Period']) * vix_history['ratio2']

        # enter position when wa.ratio < 0.95, exit otherwise
        vix_history['enter'] = vix_history.apply(lambda row: True if row['wa_ratio'] < self.enter_coef else False,
                                                 axis=1)
        # # Assume open price is previous close price
        vix_history['setup_coef'] = vix_history.apply(
            lambda row: self.deep_contango_setup_coef if row['wa_ratio'] < self.deep_contango_coef else self.setup_coef,
            axis=1)

        # Join market data from Yahoo Finance
        logging.info("Join modeling data and market data...")
        vix_history = pandas.merge(vix_history, market_data, on='date', how='left')
        # join

        # Add additional performance monitoring columns
        vix_history['capital'] = 0.0
        vix_history['daily_pnl'] = 0.0
        vix_history['unrealized_pnl'] = 0.0
        vix_history['realized_pnl'] = 0.0
        vix_history['position'] = 0.0
        vix_history['trade_logs'] = ""
        vix_history = vix_history.sort_values(by=['date'])
        vix_history['date_int'] = vix_history.apply(
            lambda row: date_utils.date_str_to_int(row['date'].strftime('%Y-%m-%d')), axis=1)
        vix_history = vix_history.reset_index(drop=True)

        return vix_history

    def get_benchmark(self, daily_rebalance=False):
        # load s&p500 index historical data
        benchmark = self.get_his_mkt_data(self.benchmark_ticker)
        benchmark['capital_benchmark'] = 0.0
        if daily_rebalance:
            for index, row in benchmark.iterrows():
                if index == 0:
                    benchmark.at[index, 'capital_benchmark'] = self.initial_capital
                else:
                    position = benchmark['capital_benchmark'].iloc[index - 1] / row['open']
                    daily_pnl = position * (row['close'] - row['open'])
                    benchmark.at[index, 'capital_benchmark'] = benchmark['capital_benchmark'].iloc[
                                                                   index - 1] + daily_pnl
        else:
            start_position = self.initial_capital / list(benchmark['open'])[0]
            for index, row in benchmark.iterrows():
                if index ==0:
                    benchmark.at[index, 'capital_benchmark'] = self.initial_capital
                else:
                    daily_pnl = (row['close'] - row['open']) * start_position
                    benchmark.at[index, 'capital_benchmark'] = benchmark['capital_benchmark'].iloc[index - 1] + daily_pnl

        benchmark = benchmark.rename(columns={'open': 'open_benchmark', 'close': 'close_benchmark'})
        return benchmark

    def execute_trade_strategy(self, data, save_output=True):
        """
        Trade Execution Engine
        :param data:
        :param save_output:
        :return:
        """
        ################# Trade Execution Strategy ####################
        # Daily rebalance if signal is enter and unrealized pnl is positive
        # Exit signal will force close positions regardless of unrealized pnl
        # Signal is lagged 1 day using previous closing ratios
        # Daily PnL is using T+1 open price to trade

        hold_flag = False
        hold_index = 0

        for index, row in data.iterrows():
            if index == 0:
                data.at[index, 'capital'] = self.initial_capital
            else:
                if data['enter'].iloc[index - 1]:
                    if not hold_flag:
                        # dynamic setup coef based on deep contango or regular contango
                        short_position = - data['capital'].iloc[index - 1] * data['setup_coef'].iloc[index - 1] / row[
                            'open']
                    else:
                        short_position = data['position'].iloc[index - 1]

                    data.at[index, 'position'] = short_position

                    daily_pnl = (row['close'] - row['open']) * short_position
                    data.at[index, 'daily_pnl'] = daily_pnl

                    # IF today's pnl is negative and position is not hold, hold the position
                    if daily_pnl < 0 and not hold_flag:
                        hold_flag = True
                        hold_index = index

                    # calculate the unrealized pnl
                    if hold_index > 0:
                        data.at[index, 'trade_logs'] = 'hold'
                        unrealized_pnl = data['daily_pnl'][hold_index:index + 1].sum()
                        realized_pnl = 0
                    else:
                        data.at[index, 'trade_logs'] = 'daily rebalance'
                        unrealized_pnl = 0
                        realized_pnl = daily_pnl

                    # Hold until realized_pnl >0
                    if hold_flag and unrealized_pnl > 0:
                        data.at[index, 'trade_logs'] = "hold rebalance"
                        realized_pnl = unrealized_pnl
                        unrealized_pnl = 0
                        hold_flag = False
                        hold_index = 0

                    data.at[index, 'unrealized_pnl'] = unrealized_pnl
                    data.at[index, 'realized_pnl'] = realized_pnl
                    data.at[index, 'capital'] = data['capital'].iloc[index - 1] + realized_pnl
                else:
                    hold_flag = False
                    hold_index = 0
                    data.at[index, 'trade_logs'] = 'closed by exit signal'
                    # strategy1: close at closing price so we have daily pnl on that day
                    # daily_pnl = (row['close']-row['open'])* data['position'].iloc[index-1]
                    # strategy2: close at open price so daily pnl is 0
                    daily_pnl = 0
                    data.at[index, 'unrealized_pnl'] = 0
                    realized_pnl = daily_pnl + data['unrealized_pnl'].iloc[index - 1]
                    data.at[index, 'capital'] = data['capital'].iloc[index - 1] + realized_pnl

        if save_output:
            data.to_csv(self.output_dir + 'short_vix_trade_logs.csv')

        return data

    def run_backtesting(self, save_output=True):
        """
        Run backtesting
        :param save_output:
        :return:
        """
        logging.info("running backtesting...")
        data = self.process_data()
        data = self.execute_trade_strategy(data, save_output)
        return data

    def print_algo_performance(self, df):
        trade_days = len(df)
        max_hold_days = self.find_max_holding_days(df)
        start_balance = self.initial_capital
        end_balance = list(df['capital'])[-1]
        total_investment_return = (end_balance - start_balance) / start_balance
        annualized_return = pow((1 + total_investment_return), 365 / trade_days) - 1

        max_unrealized_loss = numpy.nanmax(df['unrealized_pnl'] / df['capital'])
        min_unrealized_loss = numpy.nanmin(df['unrealized_pnl'] / df['capital'])
        max_realized_loss = numpy.nanmax(df['realized_pnl'] / df['capital'])
        min_realized_loss = numpy.nanmin(df['realized_pnl'] / df['capital'])

        print("trade days:{0}".format(trade_days))
        print("initial capital:{0}".format(self.initial_capital))
        print("end capital:{0}".format(round(end_balance, 2)))
        print("max hold days{0}".format(max_hold_days))
        print("total return:{0}".format("{0:.2%}".format(total_investment_return)))
        print("annualized return:{0}".format("{0:.2%}".format(annualized_return)))
        print("max unrealized loss:{0}".format("{0:.2%}".format(max_unrealized_loss)))
        print("min unrealized loss:{0}".format("{0:.2%}".format(min_unrealized_loss)))
        print("max realized loss:{0}".format("{0:.2%}".format(max_realized_loss)))
        print("min realized loss:{0}".format("{0:.2%}".format(min_realized_loss)))

    def find_max_holding_days(self, data):
        """
        Find the max holding days in the trade execution
        :param data:
        :return:
        """

        hold_days = 1
        hold_days_list = []
        for index, row in data.iterrows():
            if index > 0:
                if data['trade_logs'].iloc[index - 1] == 'hold' and row['trade_logs'] == 'hold':
                    hold_days += 1
                else:
                    hold_days_list.append(hold_days)
                    hold_days = 1
        return max(hold_days_list)

    def plot_backtesting_results(self, df, cols, fig_size=(14, 6)):
        """
        multiple plots
        :param df:
        :param cols:
        :param fig_size:
        :return:
        """
        color_list = ['r', 'g', 'y']
        df = df.set_index('date')
        plt.figure(figsize=fig_size)

        for i, col in enumerate(cols):
            plt.plot(df.index, df[col], c=color_list[i])
            plt.legend([col])

        plt.xlabel('time')
        plt.ylabel('USD')
        plt.grid(True)

    def find_future_expire_date(self, date, map, shift):
        """
        find future expire date
        :param date:
        :param map:
        :param shift:
        :return:
        """
        year = (date + relativedelta(months=+shift)).year
        month = (date + relativedelta(months=+shift)).month
        expire = map[map.expire_month == str(year) + '%02d' % month]['expire date'].iloc[0]
        return expire


if __name__ == "__main__":
    algo = ShortVixAlgo()
    benchmark = algo.get_benchmark()
    data = algo.run_backtesting()
    algo.print_algo_performance(data)
