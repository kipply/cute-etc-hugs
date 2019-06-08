#!/usr/bin/python

# ~~~~~==============   HOW TO RUN   ==============~~~~~
# 1) Configure things in CONFIGURATION section
# 2) Change permissions: chmod +x bot.py
# 3) Run in loop: while true; do ./bot.py; sleep 1; done

from __future__ import print_function

import sys
import socket
import json

# ~~~~~============== CONFIGURATION  ==============~~~~~
# replace REPLACEME with your team name!
team_name = "TEAMLOWRY"
# This variable dictates whether or not the bot is connecting to the prod
# or test exchange. Be careful with this switch!
test_mode = eval(open('env').read())

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index = 0
prod_exchange_hostname = "production"

port = 25000 + (test_exchange_index if test_mode else 0)
exchange_hostname = "test-exch-" + team_name if test_mode else prod_exchange_hostname

extra_log = open('extra_logs.txt', 'w+')


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# ~~~~~============== NETWORKING CODE ==============~~~~~


def connect():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s.connect((exchange_hostname, port))
    return s.makefile('rw', 1)


def write_to_exchange(exchange, obj):
    json.dump(obj, exchange)
    exchange.write("\n")


def read_from_exchange(exchange):
    return json.loads(exchange.readline())


# ~~~~~============== MAIN LOOP ==============~~~~~

def ID():
    return len(trades)


portfolio = {
    u'BOND': 0,
    u'VALBZ': 0,
    u'VALE': 0,
    u'GS': 0,
    u'MS': 0,
    u'WFC': 0,
    u'XLF': 0,
}
recent_book = {
    u'BOND': {},
    u'VALBZ': {},
    u'VALE': {},
    u'GS': {},
    u'MS': {},
    u'WFC': {},
    u'XLF': {},
}
trades = []


def main():
    global portfolio
    global recent_book
    global offering
    global trades

    exchange = connect()
    write_to_exchange(exchange, {"type": "hello", "team": team_name.upper()})
    hello_from_exchange = read_from_exchange(exchange)
    # A common mistake people make is to call write_to_exchange() > 1
    # time for every read_from_exchange() response.
    # Since many write messages generate marketdata, this will cause an
    # exponential explosion in pending messages. Please, don't do that!
    print("The exchange replied:", hello_from_exchange, file=sys.stderr)

    while True:
        next_message = read_from_exchange(exchange)
        extra_log.write(str(next_message))
        if next_message['type'] == "book":
            symbol = next_message['symbol']
            recent_book[symbol]['buy'] = next_message['buy']
            recent_book[symbol]['sell'] = next_message['sell']
            # if next_message['symbol'] == "BOND":
                # flip_BOND(exchange)
            etf_arbitrage(exchange)
        elif next_message['type'] == "ack":
            trades[next_message['order_id']]['status'] = "ACK"
            print("ACK")
        elif next_message['type'] == "fill":
            order_id = next_message['order_id']
            trades[order_id]['fills'].append(next_message)
            if next_message['dir'] == "BUY":
                portfolio[symbol] += next_message["size"]
            elif next_message['dir'] == "SELL":
                portfolio[symbol] -= next_message["size"]
            print(next_message)
        elif next_message['type'] == "out":
            trades[next_message['order_id']]['status'] = "OUT"
            print(bcolors.WARNING + "OUT" + bcolors.ENDC)
        elif next_message['type'] == "reject":
            print(next_message)
        elif next_message['type'] == "error":
            print(next_message)
        elif next_message['type'] == "trade":
            # Don't need to do anything
            pass
        elif next_message['type'] == "close":
            # reset everything
            portfolio = {
                u'BOND': 0,
                u'VALBZ': 0,
                u'VALE': 0,
                u'GS': 0,
                u'MS': 0,
                u'WFC': 0,
                u'XLF': 0,
            }
            recent_book = {
                u'BOND': {},
                u'VALBZ': {},
                u'VALE': {},
                u'GS': {},
                u'MS': {},
                u'WFC': {},
                u'XLF': {},
            }
            trades = []
            print(bcolors.FAIL + "RESET!!!!!!!!" + bcolors.ENDC)
        #
        # TODO: Handle server dying and restart


def buy(exchange, name, price, size):
    write_to_exchange(exchange, {
        'type': 'add',
        'order_id': ID(),
        'symbol': name,
        'dir': 'BUY',
        'price': price,
        'size': size
    })
    trades.append({
        'symbol': name,
        'price': price,
        'size': size,
        'status': 'SENT',
        'dir': 'BUY',
        'fills': []
    })


def sell(exchange, name, price, size):
    write_to_exchange(exchange, {
        'type': 'add',
        'order_id': ID(),
        'symbol': name,
        'dir': 'SELL',
        'price': price,
        'size': size
    })
    trades.append({
        'symbol': name,
        'price': price,
        'size': size,
        'status': 'SENT',
        'dir': 'SELL',
        'fills': []
    })


def flip_BOND(exchange):
    for pair in recent_book['BOND']['sell']:
        if pair[0] < 1000:
            buy(exchange, "BOND", pair[0], pair[1])
    for pair in recent_book['BOND']['buy']:
        if pair[0] > 1000:
            sell(exchange, "BOND", pair[0], pair[1])


def convert(exchange, name, dir, size):
    print("trying_to_convert", name, dir, size)
    write_to_exchange(exchange, {
        'type': 'convert',
        'order_id': ID(),
        'symbol': name,
        'dir': dir,
        'size': size
    })
    trades.append({
        'type': 'convert',
                'symbol': name,
                'price': 0,
                'size': size,
                'status': 'SENT',
                'dir': 'CONVERT',
                'fills': []
    })


def etf_arbitrage(exchange):
  xlf_sell_estimate = 0
  temp = count = volume = 0
  try: 
    for share in recent_book['XLF']['sell']:
      xlf_sell_estimate += share[0] * share[1]
      temp += share[1]
      count += 1
      if count >= 1:
        break
    volume  = min(temp, 10)
    xlf_sell_estimate /= float(temp)

    est_bond = temp = count = 0
    for share in recent_book['BOND']['buy']:
      est_bond += share[0] * share[1]
      temp += share[1]
      count += 1
      if count >= 1:
        break
    est_bond /= float(temp)

    est_gs = temp = count = 0
    for share in recent_book['GS']['buy']:
      est_gs += share[0] * share[1]
      temp += share[1]
      count += 1
      if count >= 1:
        break
    est_gs /= float(temp)

    est_ms = temp = count = 0
    for share in recent_book['MS']['buy']:
      est_ms += share[0] * share[1]
      temp += share[1]
      count += 1
      if count >= 1:
        break
    est_ms /= float(temp)

    est_wfc = temp = count = 0
    for share in recent_book['WFC']['buy']:
      est_wfc += share[0] * share[1]
      temp += share[1]
      count += 1
      if count >= 1:
        break
    est_wfc /= float(temp)

  except Exception as e: 
    return
  xlf_buy_est = (2 * est_wfc + 3 * est_ms + 2 * est_gs + 3 * est_bond) / 10.0

  print(xlf_buy_est, xlf_sell_estimate)

  if xlf_buy_est > xlf_sell_estimate: 
    buy(exchange, "XLF", int(round(xlf_sell_estimate)), volume)
  if 10 * xlf_buy_est - 100 > xlf_sell_estimate * 10 and portfolio["XLF"] >= 10: 
    convert(exchange, "XLF", "SELL", portfolio["XLF"] // 10)
    sell(exchange, "BOND", int(round(est_bond)), portfolio["XLF"] // 10 * 3)
    sell(exchange, "GS", int(round(est_gs)), portfolio["XLF"] // 10 * 2)
    sell(exchange, "MS", int(round(est_ms)), portfolio["XLF"] // 10 * 3)
    sell(exchange, "WFC", int(round(est_wfc)), portfolio["XLF"] // 10 * 2)
    print("MADE ETF TRADE FOR 10")


if __name__ == "__main__":
    main()
