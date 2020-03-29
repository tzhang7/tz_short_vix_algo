from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

import ipywidgets as widgets

from vix_trade_ui.wg_base import WidgetBase, show_ui_ct
from vix_trade_ui.wg_long_signal import WidgetLongSignal
from signal_notifier import RealTradeEngine
from config.user import User
from config.env import ticker_config_schema
from db import VixDb
import matplotlib as mpl
import matplotlib.pyplot as plt

import logging
import datetime
import time

mpl_logger = logging.getLogger('matplotlib')
mpl_logger.setLevel(logging.WARNING)


class WidgetSignal(WidgetBase):
    """Signal and Trading Position Monitoring UI"""

    # noinspection PyProtectedMember
    def __init__(self):
        """Singal UI"""
        self.user1 = User('tao', 'tzshortvix@gmail.com')
        self.flag = True
        self.db = VixDb()
        self.market_open_hour = datetime.time(8)
        self.market_close_hour = datetime.time(23, 00, 0)

        ## UI Component
        self.sl = WidgetLongSignal()

        sub_widget_tab = widgets.Tab()
        sub_widget_tab.children = [self.sl.widget, self.sl.widget]
        for ind, name in enumerate(['Long', 'Short-Spike']):
            sub_widget_tab.set_title(ind, name)

        # Buttons
        self.start_trading_bt = widgets.Button(description='Start Monitoring', layout=widgets.Layout(width='98%'),
                                               button_style='success')

        self.save_ticker_bt = widgets.Button(description='Save Ticker', layout=widgets.Layout(width='98%'),
                                             button_style='danger')

        self.start_trading_bt.on_click(self.start_trading)
        self.save_ticker_bt.on_click(self.save_ticker)

        buttons = widgets.HBox([self.start_trading_bt, self.save_ticker_bt])
        self.out = widgets.Output(layout={'border': '1px solid black'})

        self.widget = widgets.VBox([sub_widget_tab, buttons, self.out])

    def start_trading(self, bt):
        """Start Trading Button"""
        trade_engine = RealTradeEngine([self.user1], month1_ticker=self.sl.vix_month1_ticker.value,
                                       month2_ticker=self.sl.vix_month2_ticker.value)

        while True:
            trade_time = datetime.datetime.now()

            if self.market_open_hour <= trade_time.time() <= self.market_close_hour:
                signal_tbl = trade_engine.start_trading(trade_time)
                with self.out:
                    self.out.clear_output()
                    print(signal_tbl)
                time.sleep(self.sl.monitor_interval.value)

    def plot_signal(self, signal_tbl):

        migtime = [16.6, 16.5, 16.9, 17.1, 17.2, 18.1, 18.2, 18.4, 19.4, 19.3, 20.4, 20.3, 22, 21.7, 22]
        delay = [108, 98, 92, 83, 87, 77, 85, 48, 31, 58, 35, 43, 36, 31, 19]

        fig, ax = plt.subplots()

        plt.xlabel('migration speed (MB/s)')
        plt.ylabel('migration time (s); request delay (ms)')

        """set interval for y label"""
        yticks = range(10, 110, 10)
        ax.set_yticks(yticks)

        """set min and max value for axes"""
        ax.set_ylim([10, 110])
        ax.set_xlim([58, 42])

        x = [57, 56, 55, 54, 53, 52, 51, 50, 49, 48, 47, 46, 45, 44, 43]
        plt.plot(x, migtime, "x-", label="migration time")
        plt.plot(x, delay, "+-", label="request delay")

        """open the grid"""
        plt.grid(True)

        plt.legend(bbox_to_anchor=(1.0, 1), loc=1, borderaxespad=0.)

        plt.show()

    def save_ticker(self, bt):
        try:
            self.db.drop_table('vix_ticker_config')
            self.db.create_table('vix_ticker_config', ticker_config_schema)
            sql = "INSERT INTO vix_ticker_config(month1_ticker,month2_ticker,interval) VALUES ('{0}', '{1}',{2})".format(
                self.sl.vix_month1_ticker.value, self.sl.vix_month2_ticker.value, self.sl.monitor_interval.value)
            self.db.execute(sql)
            print('Ticker is saved!')
        except KeyError as e:
            print(str(e))


def show_ui():
    with show_ui_ct() as go_on:
        if not go_on:
            return

        widget = WidgetSignal()
    return widget()


if __name__ == '__main__':
    show_ui()
