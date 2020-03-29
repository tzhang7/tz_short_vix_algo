import sqlite3
import pandas as pd
from config.env import ticker_config_schema

class VixDb(object):
    def __init__(self):
        self.conn = sqlite3.connect('trading.db')
        self.c = self.conn.cursor()

    def create_table(self,tbl_name,tbl_shcema):
        sql = 'CREATE TABLE IF NOT EXISTS {0}({1})'

        tmp = ''
        for col_name,col_type in tbl_shcema.items():
            tmp+=col_name + ' ' + col_type + ','

        sql = sql.format(tbl_name, tmp[:-1])
        self.execute(sql)

    def run_query(self, sql):
        df = pd.read_sql(sql, self.conn)
        return df

    def execute(self, sql):
        self.c.execute(sql)
        self.conn.commit()

    def drop_table(self, tbl_name):
        sql='DROP TABLE {0}'.format(tbl_name)
        self.execute(sql)

if __name__ == '__main__':
    db = VixDb()
    db.create_table('vix_ticker_config', ticker_config_schema)

