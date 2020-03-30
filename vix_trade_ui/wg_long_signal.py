import os
import ipywidgets as widgets
from short_vix_algo import ShortVixAlgo
import datetime
from db import VixDb


class WidgetLongSignal(object):
    """Long Signal UI"""

    def __init__(self):
        """Init"""
        # 初始资金
        trade_strategy_engine = ShortVixAlgo()
        db = VixDb()
        config = db.run_query('select *from vix_ticker_config')


        vix_month1_ticker = config['month1_ticker'].iloc[0] if len(config)>0 else 'VIJ20'
        vix_month2_ticker = config['month2_ticker'].iloc[0] if len(config) > 0 else 'VIK20'
        interval = config['interval'].iloc[0] if len(config) > 0 else 10
        tvix_px = config['tvix_px'].iloc[0] if len(config) > 0 else 390.01
        upro_px = config['upro_px'].iloc[0] if len(config) > 0 else 26.32
        tvix_qty = config['tvix_qty'].iloc[0] if len(config) > 0 else 36
        upro_qty = config['upro_qty'].iloc[0] if len(config) > 0 else 380

        self.vix_month1_ticker = widgets.Text(
            value=vix_month1_ticker,
            placeholder='Type something',
            description='Mth1 Ticker:',
            disabled=False
        )

        self.vix_month2_ticker = widgets.Text(
            value=vix_month2_ticker,
            placeholder='Type something',
            description='Mth2 Ticker:',
            disabled=False
        )

        next_expire = trade_strategy_engine.find_future_expire_date(datetime.date.today(),
                                                                    trade_strategy_engine.expire_date_mapping, 1)
        self.delivery_date = widgets.Text(
            value=next_expire.strftime("%m/%d/%Y"),
            placeholder='Type something',
            description='Expire date',
            disabled=False

        )

        self.monitor_interval = widgets.IntText(
            value=interval,
            description='Interval:',
            disabled=False
        )
        self.tvix_px = widgets.FloatText(
            value=tvix_px,
            description='TVIX px:',
            disabled=False
        )
        self.upro_px = widgets.FloatText(
            value=upro_px,
            description='UPRO px:',
            disabled=False
        )
        self.tvix_qty = widgets.IntText(
            value=tvix_qty,
            description='TVIX qty:',
            disabled=False
        )
        self.upro_qty = widgets.IntText(
            value=upro_qty,
            description='UPRO Qty:',
            disabled=False
        )
        self.capital=widgets.IntText(
            value=20000,
            description='Capital:',
            disabled=False
        )

        tickers_wg = widgets.HBox(
            [self.vix_month1_ticker, self.vix_month2_ticker, self.delivery_date])

        trade_wg1 = widgets.HBox(
            [self.tvix_px, self.upro_px,self.monitor_interval])

        trade_wg2 = widgets.HBox(
            [self.tvix_qty, self.upro_qty,self.capital])
        self.widget = widgets.VBox([tickers_wg, trade_wg1, trade_wg2])
