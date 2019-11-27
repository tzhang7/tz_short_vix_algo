import datetime
import pandas
import numpy


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

    @classmethod
    def df_empty(cls, schema, index=None):
        """
        Create an empty dataframe
        :param schema: is a dictionary, key is the column name, value is the dtype
        :return:
        """

        df = pandas.DataFrame(index=index)
        for c, d in zip(schema.keys(), schema.values()):
            df[c] = pandas.Series(dtype=d)
        return df

    @classmethod
    def addRow(cls, df, ls):
        """
        Given a dataframe and a list, append the list as a new row to the dataframe.

        :param df: <DataFrame> The original dataframe
        :param ls: <list> The new row to be added
        :return: <DataFrame> The dataframe with the newly appended row
        """

        numEl = len(ls)

        newRow = pandas.DataFrame(numpy.array(ls).reshape(1, numEl), columns=list(df.columns))

        df = df.append(newRow, ignore_index=True)

        return df
