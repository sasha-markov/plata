
"""
helpers.py
"""

import csv
import json
import time

import requests

API_KEY = '5XR4CQOINA0WR14S'
RESPONSE_FILE = '../response.json'


def get_localtime():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

def load_currencies(csvfile):
    with open(csvfile) as f:
        return set([row['currency code'] for row in csv.DictReader(f)])

def exchange(from_currency, to_currency, api_key):
    phys = load_currencies('../physical_currency_list.csv')
    digit = load_currencies('../digital_currency_list.csv')

    if (from_currency in phys | digit) and (to_currency in phys | digit):
        function = 'CURRENCY_EXCHANGE_RATE'
        url = (f'https://www.alphavantage.co/query?function={function}'
               + f'&from_currency={from_currency}'
               + f'&to_currency={to_currency}'
               + f'&apikey={API_KEY}')
        with requests.get(url) as request, open(RESPONSE_FILE, 'a+') as f:
            d = request.json()
            json.dump(d, f)
            f.write(' \n')
            if d.get('Error Message'):
                print(d.get('Error Message'))
                return None
            else:         
                rate = d['Realtime Currency Exchange Rate']['5. Exchange Rate']
                return float(rate)
    else:
        print(f'I do not know {from_currency} or {to_currency}!')
        return None
    
def get_rates(currencies):
    rates = []
    i = 1
    for currency in currencies:
        if i == 6:
            time.sleep(65)    # www.alphavantage.com allows
            i = 1             # 5 requests in 60 seconds
        if currency == 'USD':
            rate = 1.0
        else:
            try:
                rate = exchange(currency, 'USD', API_KEY)
            except:
                rate = None
        if rate == 0:         # some stablecoins zeroed
            rate = 1.0
        rates.append([currency, rate])
        i += 1
    return dict(rates)
