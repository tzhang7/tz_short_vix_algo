__author__ = "Tao Zhang"
__copyright__ = "Copyright 2019, The VIX short Strategy"
__email__ = "uncczhangtao@yahoo.com"

import requests
import random
import time
import socket
import http.client
from bs4 import BeautifulSoup


def get_barchart_real_time_data(ticker):
    url = 'https://www.barchart.com/futures/quotes/{}'.format(ticker)
    header = {
        'authority': 'www.barchart.com',
        'method': 'GET',
        'path': '/futures/quotes/{0}'.format(ticker),
        'scheme': 'https',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'zh-CN,zh;q=0.9,zh-TW;q=0.8',
        'cache-control': 'max-age=0',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'none',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.97 Safari/537.36'
    }

    timeout = random.choice(range(80, 180))

    try:
        rep = requests.get(url, headers=header, timeout=timeout)
        rep.encoding = 'utf-8'
    except socket.timeout as e:
        print(e)
        time.sleep(random.choice(range(8, 15)))
    except socket.error as e:
        print(e)
        time.sleep(random.choice(range(8, 15)))
    except http.client.BadStatusLine as e:
        print('5:', e)
        time.sleep(random.choice(range(30, 80)))

    except http.client.IncompleteRead as e:
        print('6:', e)
        time.sleep(random.choice(range(5, 15)))

    html_text = rep.text

    # Parse data using beautifulSoup
    bs = BeautifulSoup(html_text, 'html.parser')
    body = bs.body
    data = body.find('div', {'id': 'main-content-column'})
    results = data.find_all('div', class_='page-title symbol-header-info')

    for result in results:
        data_dic = result.attrs['data-ng-init']

    temp = data_dic.split("(")[1]
    if "}" in temp and ")" in temp:
        data_dic = temp.replace(")",'').replace('true', 'True')
    else:
        data_dic = temp + '"}'
    data_dic = eval(data_dic)
    last_price = float(data_dic['lastPrice'][:-1]) if 's' in data_dic['lastPrice'] else float(data_dic['lastPrice'])
    return last_price


if __name__ == '__main__':
    #VIZ19, VIF20, TVIX, VIY00
    px = get_barchart_real_time_data('VIY00')
    print(px)
