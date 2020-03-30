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

        self.save_ticker_bt = widgets.Button(description='Save Config', layout=widgets.Layout(width='98%'),
                                             button_style='danger')

        self.calc_qty_bt = widgets.Button(description='Calc Qty', layout=widgets.Layout(width='98%'),
                                          button_style='info')

        self.start_trading_bt.on_click(self.start_trading)
        self.save_ticker_bt.on_click(self.save_ticker)
        self.calc_qty_bt.on_click(self.calc_qty)

        buttons = widgets.HBox([self.start_trading_bt, self.calc_qty_bt, self.save_ticker_bt])
        self.out = widgets.Output(layout={'border': '1px solid black'})

        self.trade_engine = RealTradeEngine([self.user1], month1_ticker=self.sl.vix_month1_ticker.value,
                                            month2_ticker=self.sl.vix_month2_ticker.value)

        self.widget = widgets.VBox([sub_widget_tab, buttons, self.out])

    def start_trading(self, bt):
        """Start Trading Button"""

        while True:
            trade_time = datetime.datetime.now()

            if self.market_open_hour <= trade_time.time() <= self.market_close_hour:
                self.trade_engine.get_market_data()
                signal_tbl = self.trade_engine.start_trading(trade_time)
                current_wa_ratio = signal_tbl.tail(1)['wa_ratio'].iloc[0]
                if len(signal_tbl) > 5:
                    signal_tbl = signal_tbl.tail(6)
                with self.out:
                    self.out.clear_output()
                    self.plot_signal(signal_tbl,self.trade_engine.trade_market_px, self.trade_engine.hedge_market_px,
                                       current_wa_ratio)
                    print(signal_tbl)
                time.sleep(self.sl.monitor_interval.value)


    def plot_signal(self, signal_tbl, tvix_px, upro_px, wa_ratio):
        # Plot signal and PNL
        capital_original = round(
            self.sl.upro_px.value * self.sl.upro_qty.value + self.sl.tvix_px.value * self.sl.tvix_qty.value, 2)
        current_capital = round(self.sl.upro_qty.value * upro_px + self.sl.tvix_qty.value * tvix_px, 2)
        pnl = round(current_capital - capital_original, 2)
        sumamry = " Current Ratio:{0}, In Position Capital:{1}, Current Capital:{2}, Pnl:{3}".format(wa_ratio,
                                                                                                     capital_original,
                                                                                                     current_capital,
                                                                                                     pnl)
        print(sumamry)
        time = signal_tbl['time'].tolist()
        signal = signal_tbl['wa_ratio'].tolist()
        signal = [float(x) for x in signal]
        fig_size = (14, 6)
        plt.figure(figsize=fig_size)

        red_line = [1.17 for i in range(len(time))]
        yellow_line = [1.20 for i in range(len(time))]
        green_line = [1.25 for i in range(len(time))]

        original_capital_line = [capital_original for i in range(len(time))]
        current_capital_line = [current_capital for i in range(len(time))]

        plt.subplot(1, 2, 1)
        plt.plot(time, red_line, "-", label="red", color="red")
        plt.plot(time, yellow_line, "-", label="red", color="yellow")
        plt.plot(time, green_line, "-", label="red", color="green")
        plt.plot(time, signal, "ko-", label="signal", color="blue")
        plt.legend(['red','yellow','green','blue'])
        plt.xlabel('time')
        plt.ylabel('signal')

        plt.subplot(1, 2, 2)
        plt.plot(time, original_capital_line, "-", label="red", color="red")
        plt.plot(time, current_capital_line, "ko-", label="red", color="blue")
        plt.legend(['original capital', 'current capital'])
        plt.xlabel('time')
        plt.ylabel('Capital')

        plt.tight_layout()
        plt.show()

    def save_ticker(self, bt):
        try:
            self.db.drop_table('vix_ticker_config')
            self.db.create_table('vix_ticker_config', ticker_config_schema)
            sql = "INSERT INTO vix_ticker_config(month1_ticker,month2_ticker,interval,tvix_px,upro_px,tvix_qty,upro_qty) VALUES ('{0}', '{1}',{2}, {3}, {4}, {5}, {6})".format(
                self.sl.vix_month1_ticker.value,
                self.sl.vix_month2_ticker.value,
                self.sl.monitor_interval.value,
                self.sl.tvix_px.value,
                self.sl.upro_px.value,
                self.sl.tvix_qty.value,
                self.sl.upro_qty.value)
            self.db.execute(sql)
            print('Config is saved!')
        except KeyError as e:
            print(str(e))

    def calc_qty(self, bt):
        capital = self.sl.capital.value
        self.trade_engine.get_market_data()
        tvix_qty = int(capital / 2 / self.trade_engine.trade_market_px)
        upro_qty = int(capital / 2 / self.trade_engine.hedge_market_px)
        with self.out:
            self.out.clear_output()
            print(
                "Capital:{0}| TVIX Qty:{1}| UPRO Qty:{2}| TVIX px:{3}| UPRO px:{4}".format(capital, tvix_qty, upro_qty,
                                                                                           self.trade_engine.trade_market_px,
                                                                                           self.trade_engine.hedge_market_px))


def show_ui():
    with show_ui_ct() as go_on:
        if not go_on:
            return

        widget = WidgetSignal()
    return widget()


if __name__ == '__main__':
    show_ui()
