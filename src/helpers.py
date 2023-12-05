
"""
helpers.py
"""

import csv
import json
import time

import requests

API_KEY = '5XR4CQOINA0WR14S'
COIN_MARKET_CAP_API_KEY = 'befd683e-e690-4f62-8cdd-16d7797afd79'
RESPONSE_FILE = '../response.json'
SETTINGS_FILENAME = '/home/markov/.plata-gtk/settings.json'

def load_settings():
    with open(SETTINGS_FILENAME, 'r') as f:
        return json.load(f)

settings = load_settings()

# settings = {
#     'recent_db_files': [],
# }


def dump_settings():
    with open(SETTINGS_FILENAME, 'w') as f:
        json.dump(settings, f)

def get_localtime():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

def load_currencies(csvfile):
    with open(csvfile) as f:
        return set([row['currency code'] for row in csv.DictReader(f)])

def exchange_crypto(#from_currency: str,
                    #to_currency: str,
                    api_key = COIN_MARKET_CAP_API_KEY) -> float or None:
    url_sandbox = 'https://sandbox-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    url = 'https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest'
    parameters = {
        'start':'1',
        'limit':'15',
        'convert':'USD'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': 'befd683e-e690-4f62-8cdd-16d7797afd79',
    }
    session = requests.Session()
    session.headers.update(headers)
    try:
        response = session.get(url, params=parameters)
        data = json.loads(response.text)
        return data
    except (requests.ConnectionError,
            requests.Timeout,
            requests.TooManyRedirects) as e:
        print(e)

def exchange(from_currency, to_currency, api_key = API_KEY) -> float or None:
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
            if d.get('Information'):
                print(d.get('Information'))
                return None
            else:         
                rate = d['Realtime Currency Exchange Rate']['5. Exchange Rate']
                return float(rate)
    else:
        print(f'I do not know {from_currency} or {to_currency}!')
        return None
    
def get_rates_from_market(currencies: set, queue) -> dict:
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
        queue.put(f'{currency} updated')
        i += 1
    return dict(rates)
