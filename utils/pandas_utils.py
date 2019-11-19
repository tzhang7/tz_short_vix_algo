import datetime


class PandasUtils(object):
    DEFAULT_TIME_FMT = '%d %B %Y'

    @classmethod
    def convert_date_str_to_datetime(cls, df, col, format=DEFAULT_TIME_FMT):
        """
        convert date str to datetime
        :param df:
        :param col:
        :param format:
        :return:
        """
        df[col] = df.apply(lambda row: datetime.datetime.strptime(row[col], format), axis=1)

        return df
