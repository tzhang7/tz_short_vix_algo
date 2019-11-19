# -*- coding: utf-8 -*-
# @Time    : 9/21/19 17:19
# @Author  : Tao Zhang

# -*- encoding:utf-8 -*-
"""
    Date Time Utils
"""

from datetime import datetime as dt
import datetime
import time
import six
import pandas as pd

try:
    from dateutil.relativedelta import relativedelta as timedelta
except ImportError:
    from datetime import timedelta

"""Default Date Time Format Across Project"""
K_DEFAULT_DT_FMT = "%Y-%m-%d"

def pd_str_col_to_datetime(df, col_name, fmt=K_DEFAULT_DT_FMT):
    """
    Convert the string object to datetime object
    :param df: pandas dataframe
    :param col_name: date column
    :param fmt: default format
    :return: pandas dataframe
    """

    df[col_name] = pd.to_datetime(df[col_name], format=fmt)
    return df

def str_to_datetime(date_str, fmt=K_DEFAULT_DT_FMT, fix=True):
    """
    Convert date string to datetime.datetime object eg. '2016-01-01' －> datetime.datetime(2016, 1, 1, 0, 0)
    :param date_str: %Y-%m-%d format string，eg. '2016-01-01'
    :param fmt: if date string is not %Y-%m-%d, pass the format
    :param fix: whether to fix the date format，eg. 2016-1-1 fix 2016-01-01
    :return: datetime.datetime object，eg. datetime.datetime(2016, 1, 1, 0, 0)
    """
    if fix and fmt == K_DEFAULT_DT_FMT:
        # only format to %Y-%m-%d format
        date_str = fix_date(date_str)

    return dt.strptime(date_str, fmt)


def str_to_datetime_fast(date_str, split='-', fix=True):
    """
    Convert date string to datetime.datetime object fast mode, performance is improved twice than str_to_datetime()
    :param date_str: if date string is not %Y-%m-%d, pass the format
    :param split: split for year month and day, default is '-'
    :param fix: whether to fix the date format，eg. 2016-1-1 fix 2016-01-01
    :return: datetime.datetime object，eg. datetime.datetime(2016, 1, 1, 0, 0)
    """
    if fix and split == '-':
        date_str = fix_date(date_str)
    y, m, d = date_str.split(split)
    return dt(int(y), int(m), int(d))


def datetime_to_str(dt_obj):
    """
    Convert datetime object to string, inverse function for str_to_datetime()
    :param dt_obj: datetime.datetime object
    :return: str object eg. '2016-01-01'
    """
    return str(dt_obj.date())[:10]


def timestamp_to_str(ts):
    """
    To treat pandas.tslib.Timestamp object, object convert to str object, only keep to date，e.g. return 2016-01－01
    :param ts: pandas.tslib.Timestamp object，eg. Timestamp('2016-01-01 00:00:00')
    :return: e.g. 2016-01－01 str object
    """
    try:
        s_date = str(ts.to_pydatetime().date())[:10]
    except:
        s_date = str(ts.to_datetime().date())[:10]
    return s_date


def date_str_to_int(date_str, split='-', fix=True):
    """
    eg. 2016-01-01 -> 20160101
    Fast mode
    :param date_str: %Y-%m-%d format str object
    :param split: split for year month and day, default is '-'
    :param fix: whether to fix the date format，eg. 2016-1-1 fix 2016-01-01
    :return: int type time
    """
    if fix and split == '-':
        # 只针对%Y-%m-%d形式格式标准化日期格式
        date_str = fix_date(date_str)
    string_date = date_str.replace(split, '')
    return int(string_date)


def fix_date(date_str):
    """
    Standardize the date format:
                eg. 2016-1-1 fix 2016-01-01
                eg. 2016:01-01 fix 2016-01-01
                eg. 2016,01 01 fix 2016-01-01
                eg. 2016/01-01 fix 2016-01-01
                eg. 2016/01/01 fix 2016-01-01
                eg. 2016/1/1 fix 2016-01-01
                eg. 2016:1:1 fix 2016-01-01
                eg. 2016 1 1 fix 2016-01-01
                eg. 2016 01 01 fix 2016-01-01
                .............................
    :param date_str: date format str
    :return: Standardize date string
    """
    if date_str is not None:
        if isinstance(date_str, six.string_types):
            # eg, 2016:01-01, 201601-01, 2016,01 01, 2016/01-01 -> 20160101
            date_str = ''.join(list(filter(lambda c: c.isdigit(), date_str)))

        date_str = fmt_date(date_str)
        y, m, d = date_str.split('-')
        if len(m) == 1:
            # add 0 to month
            m = '0{}'.format(m)
        if len(d) == 1:
            # add 0 to day
            d = '0{}'.format(d)
        date_str = "%s-%s-%s" % (y, m, d)
    return date_str


def fmt_date(convert_date):
    """
    e.g. convert 20160101 to 2016-01-01 format
    :param convert_date:
    :return: %Y-%m-%d format string
    """
    if isinstance(convert_date, float):
        # float to int
        convert_date = int(convert_date)
    convert_date = str(convert_date)

    if len(convert_date) > 8 and convert_date.startswith('20'):
        # eg '20160310000000000'
        convert_date = convert_date[:8]

    if '-' not in convert_date:
        if len(convert_date) == 8:
            # 20160101 to 2016-01-01
            convert_date = "%s-%s-%s" % (convert_date[0:4],
                                         convert_date[4:6], convert_date[6:8])
        elif len(convert_date) == 6:
            # 201611 to 2016-01-01
            convert_date = "%s-0%s-0%s" % (convert_date[0:4],
                                           convert_date[4:5], convert_date[5:6])
        else:
            raise ValueError('fmt_date: convert_date fmt error {}'.format(convert_date))
    return convert_date


def diff(start_date, end_date, check_order=True):
    """
    Calc the days between two dates
    :param start_date: str object or int object，if √=True int object most efficient
    :param end_date: str object or int object，if check_order=True int object most efficient
    :param check_order: check if end_date > start_date, default as True
    :return:
    """

    # First standardize the format
    start_date = fix_date(start_date)
    end_date = fix_date(end_date)

    if check_order and isinstance(start_date, six.string_types):
        # start_date convert to int
        start_date = date_str_to_int(start_date)

    if check_order and isinstance(end_date, six.string_types):
        # end_date convert to int
        end_date = date_str_to_int(end_date)

    # check if end_date > start_date, default as True
    if check_order and start_date > end_date:
        # if start_date > end_date then exchange
        tmp = end_date
        end_date = start_date
        start_date = tmp

    # fmt_date，if check_order as False, the following will not be executed
    if isinstance(start_date, int):
        # noinspection PyTypeChecker
        start_date = fmt_date(start_date)
    if isinstance(end_date, int):
        # noinspection PyTypeChecker
        end_date = fmt_date(end_date)

    # if not check_order, the following will be executed
    sd = str_to_datetime(start_date)
    ed = str_to_datetime(end_date)

    return (ed - sd).days


def current_date_int():
    """
    get curent date in int
    :return: date in int
    """
    date_int = 0
    # first get string
    today = current_str_date()
    # convert string to int manually is better than the API
    today_array = today.split("-")
    if len(today_array) == 3:
        date_int = int(today_array[0]) * 10000 + int(today_array[1]) * 100 + int(today_array[2])
    return date_int


def current_str_date():
    """
    Get today date in string，only keep to date，return e.g. 2016-01－01
    :return: e.g. 2016-01－01 string object
    """
    return str(datetime.date.today())


def week_of_date(date_str, fmt=K_DEFAULT_DT_FMT, fix=True):
    """
    Input '2016-01-01' Convert to the number in week，int 0-6 responds Monday to Sunday
    :param date_str: str object
    :param fmt: date format
    :param fix: whether to fix the date format，eg. 2016-1-1 fix 2016-01-01
    :return: int 0-6 responds Monday to Sunday
    """

    if fix and fmt == K_DEFAULT_DT_FMT:
        date_str = fix_date(date_str)
    return dt.strptime(date_str, fmt).weekday()


def begin_date(pre_days, date_str=None, split='-', fix=True):
    """
    return the date string object as date_str - pre_days
        eg:
            pre_days = 2
            date_str = '2017-02-14'
            result = '2017-02-12'

            pre_days = 365
            date_str = '2016-01-01'
            result = '2015-01-01'

        if pre_days is negative，then we ad days：
        eg:
            pre_days = -365
            date_str = '2016-01-01'
            result = '2016-12-31'
    :param pre_days: pre_days, int
    :param date_str: date_str, default: current_str_date()
    :param split:
    :param fix: whether to fix the date format，eg. 2016-1-1 fix 2016-01-01
    :return: date str object
    """

    if date_str is None:
        date_str = current_str_date()
        fix = False
    dt_time = str_to_datetime_fast(date_str, split=split, fix=fix)
    return str(dt_time + timedelta(days=-pre_days))[:10]


def time_seconds():
    """
    get curent time in seconds, return float
    :return:  float eg. 1498381468.38095
    """
    return time.time()


def time_zone():
    """return time zone as int"""
    return time.timezone
