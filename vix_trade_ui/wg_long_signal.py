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

        self.vix_month1_ticker = widgets.Text(
            value=config['month1_ticker'].iloc[0],
            placeholder='Type something',
            description='Mth1 Ticker:',
            disabled=False
        )

        self.vix_month2_ticker = widgets.Text(
            value=config['month2_ticker'].iloc[0],
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
            value=config['interval'].iloc[0],
            description='Interval:',
            disabled=False
        )
        tickers_wg = widgets.HBox(
            [self.vix_month1_ticker, self.vix_month2_ticker, self.delivery_date])


        self.widget = widgets.VBox([tickers_wg, self.monitor_interval])
