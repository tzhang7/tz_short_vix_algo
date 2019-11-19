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

register_matplotlib_converters()
locale.setlocale(locale.LC_ALL, 'en_US')


class ShortVixAlgo(object):
    """
    Short VIX Algorithm, medium trading frequency
    """

    def __init__(self,
                 setup_coef=0.3,
                 enter_coef=0.95,
                 start_trading_date="2011-01-01",
                 end_trading_date=date_utils.current_str_date(),
                 ticker='TVIX',
                 initial_capital=10000):

        self.data_dir = os.path.abspath(os.path.dirname(__file__)) + '/data/'
        self.his_data_file = 'vix-funds-models-no-formulas.xlsx'
        self.cobe_future_expire_date_mapping = 'calendar.txt'
        self.setup_coef = setup_coef
        self.enter_coef = enter_coef
        self.start_trading_date = date_utils.str_to_datetime_fast(start_trading_date)
        self.end_trading_date = date_utils.str_to_datetime_fast(end_trading_date)
        self.ticker = ticker
        self.initial_capital = initial_capital

    def get_mkt_data(self):
        loader = YahooDataLoader(self.ticker)
        return loader.kline(start=date_utils.datetime_to_str(self.start_trading_date))

    def process_data(self):
        """
        Create modeling data
        :return:
        """
        # load ticker market data
        logging.info('Loading Market Data from Yahoo Finance...')
        market_data = self.get_mkt_data()[['open', 'close', 'volume', 'high', 'low']].reset_index()

        logging.info('Loading Modeling Data...')
        # load historical futures and VIX data, and calc ratios
        vix_history = pandas.read_excel(self.data_dir + self.his_data_file)
        vix_history = vix_history[['Date', '1st mth', '2nd mth', 'VIX']]
        vix_history = vix_history.rename(columns={'Date': 'date'})
        vix_history = vix_history[
            (vix_history['date'] >= self.start_trading_date) & (vix_history['date'] <= self.end_trading_date)]

        # load future expire date mapping
        expire_date_mapping = pandas.read_csv(self.data_dir + self.cobe_future_expire_date_mapping)
        expire_date_mapping = PandasUtils.convert_date_str_to_datetime(expire_date_mapping, 'expire date')
        expire_date_mapping['expire_month'] = expire_date_mapping.apply(lambda row: row['expire date'].strftime('%Y%m'),
                                                                        axis=1)
        # find the current, previous and next expire date based on the mapping
        vix_history['current_expire'] = vix_history.apply(
            lambda row: self.find_future_expire_date(row['date'], expire_date_mapping, 0), axis=1)
        vix_history['previous_expire'] = vix_history.apply(
            lambda row: self.find_future_expire_date(row['date'], expire_date_mapping, -1), axis=1)
        vix_history['next_expire'] = vix_history.apply(
            lambda row: self.find_future_expire_date(row['date'], expire_date_mapping, 1), axis=1)

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
        # vix_history['open'] = vix_history['close'].shift(1)

        # Join market data from Yahoo Finance
        logging.info("Join modeling data and market data...")
        vix_history = pandas.merge(vix_history, market_data, on='date', how='left')

        vix_history['capital'] = 0.0
        vix_history['win'] = 0
        vix_history['pnl'] = 0.0
        vix_history = vix_history.sort_values(by=['date'])
        vix_history['date_int'] = vix_history.apply(
            lambda row: date_utils.date_str_to_int(row['date'].strftime('%Y-%m-%d')), axis=1)
        vix_history = vix_history.reset_index(drop=True)

        return vix_history

    def run_backtesting(self):
        """
        Run Backtesting
        :return:
        """
        data = self.process_data()

        negative_pnl_flag = False
        open = -1
        # daily compounding: if no exit signal received, force close the order and rebalance
        for index, row in data.iterrows():
            if index == 0:
                # initial setup
                data.at[index, 'capital'] = self.initial_capital
                row['capital'] = self.initial_capital
            else:
                if data['enter'].iloc[index - 1]:
                    # if yesterday signal is open, short position today and close it end of the day
                    # if pnl is negative, don't rebalance.
                    short_position = data['capital'].iloc[index - 1] * self.setup_coef / row['open']

                    pnl = (row['open'] - row['close']) * short_position
                    if pnl < 0:
                        # still hold the position, the pnl will not be realized.
                        data.at[index, 'capital'] = data['capital'].iloc[index - 1]

                    else:
                        data.at[index, 'capital'] = data['capital'].iloc[index - 1] + pnl

                    if pnl < 0 and not negative_pnl_flag:
                        open = row['open']
                        negative_pnl_flag = True

                    data.at[index, 'win'] = 1 if row['open'] - row['close'] > 0 else 0
                    data.at[index, 'pnl'] = pnl / data['capital'].iloc[index - 1]
                else:
                    # hold 0 position when yesterday signal is exit
                    if open >0:
                        pnl = open - row['close']
                        negative_pnl_flag = False
                        data.at[index, 'capital'] = data['capital'].iloc[index - 1] + pnl
                    else:
                        data.at[index, 'capital'] = data['capital'].iloc[index - 1]

        return data

    def print_algo_performance(self, df):
        trade_days = len(df)
        start_balance = self.initial_capital
        end_balance = list(df['capital'])[-1]
        total_investment_return = (end_balance - start_balance) / start_balance
        annualized_return = pow((1 + total_investment_return), 365 / trade_days) - 1
        maximum_loss = min(df['pnl'])
        maximum_gain = max(df['pnl'])
        win_rate = len(df[df['win'] == 1]) / trade_days

        print("trade days:{0}".format(trade_days))
        print("initial capital:{0}".format(locale.format_string("%d", self.initial_capital, grouping=True)))
        print("end capital:{0}".format(locale.format_string("%d", round(end_balance, 2), grouping=True)))
        print("total return:{0}".format("{0:.2%}".format(total_investment_return)))
        print("annualized return:{0}".format("{0:.2%}".format(annualized_return)))
        print("maximun loss:{0}".format("{0:.2%}".format(maximum_loss)))
        print("maximun gain:{0}".format("{0:.2%}".format(maximum_gain)))
        print("win rate:{0}".format("{0:.2%}".format(win_rate)))

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
    data = algo.run_backtesting()
    algo.print_algo_performance(data)
