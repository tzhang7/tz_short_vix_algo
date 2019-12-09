__author__ = "Tao Zhang"
__copyright__ = "Copyright 2019, The VIX short Strategy"
__email__ = "uncczhangtao@yahoo.com"

from utils.pandas_utils import PandasUtils


class User(object):

    def __init__(self,
                 name,
                 email,
                 capital=30000,
                 setup_coef=0.33,
                 deep_contango_setup_coef=0.4,
                 enter_coef=0.95,
                 deep_contango_coef=0.90,
                 print_log=True
                 ):

        self.name = name
        self.email = email
        self.capital = capital
        self.setup_coef = setup_coef
        self.deep_contango_setup_coef = deep_contango_setup_coef
        self.enter_coef = enter_coef
        self.deep_contango_coef = deep_contango_coef
        self.trade_log_schema = {'time': 'datetime64[ns]',
                                 'user': str,
                                 'vix_mth1': float,
                                 'vix_mth2': float,
                                 'vix_spot': float,
                                 'wa_ratio': float,
                                 'market_px': float,
                                 'capital': float,
                                 'position': float,
                                 'log': str,
                                 'email_sent': bool}
        self.trade_log_tbl = PandasUtils.df_empty(self.trade_log_schema)
        self.open_email =True
        self.only_show_signal = True
        self.print_log = print_log
