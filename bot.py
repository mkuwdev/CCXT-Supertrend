import ccxt
import ta
import schedule
import config
import pandas as pd
from datetime import datetime
pd.set_option('display.max_rows', None)

import warnings
warnings.filterwarnings('ignore')

import numpy as np
import time

exchange = ccxt.kraken({
    "apiKey": config.KRAKEN_API_KEY,
    "secret": config.KRAKEN_SECRET_KEY
})

print(exchange.fetch_balance())

symbol = 'ETH/USD'

def tr(df):

    df['previous_close'] = df['close'].shift(1)

    df['high-low'] = df['high'] - df['low']
    df['high-pc'] = abs(df['high'] - df['previous_close'])
    df['low-pc'] = abs(df['low'] - df['previous_close'])

    return df[['high-low', 'high-pc', 'low-pc']].max(axis = 1)

def atr(df, period = 14):

    df['tr'] = tr(df)

    print("Calculating true range")

    the_atr = df['tr'].rolling(period).mean()

    return the_atr

def supertrend(df, period = 7, multiplier = 3):

    print("Calculating supertrend")
    df['atr'] = atr(df, period = period)

    # basic upper band = ((high + low) / 2) + (multiplier * atr)
    # basic lower band = ((high + low) / 2) - (multiplier * atr)
    hl2 = ((df['high'] + df['low']) / 2)
    df['upperband'] = hl2 + (multiplier * df['atr'])
    df['lowerband'] = hl2 - (multiplier * df['atr'])

    df['in_uptrend'] = True

    for current in range(1, len(df.index)):
        previous = current - 1

        if df['close'][current] > df['upperband'][previous]:
            df['in_uptrend'][current] = True
        elif df['close'][current] < df['lowerband'][previous]:
            df['in_uptrend'][current] = False
        else:
            df['in_uptrend'][current] = df['in_uptrend'][previous]

            if df['in_uptrend'][current] and df['lowerband'][current] < df['lowerband'][previous]:
                df['lowerband'][current] = df['lowerband'][previous]

            if (not df['in_uptrend'][current]) and df['upperband'][current] > df['upperband'][previous]:
                df['upperband'][current] = df['upperband'][previous]

    return(df)

first_entry = True
in_position = False

def execute_buy_sell(df):

    global first_entry
    global in_position

    print("Checking for buys and sells")
    print(df.tail(5))

    last_row_index = len(df.index) - 1
    previous_row_index = last_row_index - 1

    if first_entry: 
        
        if df['in_uptrend'][last_row_index] and not in_position:

            print("Time to enter market, Buy")
            order = exchange.create_market_buy_order('LTC/USDT', 0.05)
            print(order)
            in_position = True
            first_entry = False

    else:

        if not df['in_uptrend'][previous_row_index] and df['in_uptrend'][last_row_index]:
            print("Change to uptrend, Buy")

            if not in_position:
                order = exchange.create_market_buy_order('LTC/USDT', 0.05)
                print(order)
                in_position = True
            else:
                print("Already in position")
            
        
        if df['in_uptrend'][previous_row_index] and not df['in_uptrend'][last_row_index]:
            print("Change to downtrend, Sell")

            if in_position:
                order = exchange.create_market_sell_order('LTC/USDT', 0.05)
                print(order)
                in_position = False
            else:
                print("Already out of position")

def run_bot():
    print(f"Fetching new bars for {datetime.now().isoformat()}")
    bars = exchange.fetchOHLCV(symbol, timeframe='1m', limit=100)
    df = pd.DataFrame(bars[:-1], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    # print(df)

    supertrend_data = supertrend(df)
    execute_buy_sell(supertrend_data)

schedule.every(15).seconds.do(run_bot)

# supertrend(df)

while True:
    schedule.run_pending()
    time.sleep(1)



