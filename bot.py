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
test_mode = True

# This setting changes which test exchange is connected to.
# 0 is prod-like
# 1 is slower
# 2 is empty
test_exchange_index = 0
prod_exchange_hostname = "production"

port = 25000 + (test_exchange_index if test_mode else 0)
exchange_hostname = "test-exch-" + team_name if test_mode else prod_exchange_hostname

extra_log = open('extra_logs.txt', 'w+')

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

portfolio = {
    "BOND": 0,
    "VALBZ": 0,
    "VALE": 0,
    "GS": 0,
    "MS": 0,
    "WFC": 0,
    "XLF": 0,
}

def ID():
    return len(trades)

positions = {
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
            print(recent_book)
            recent_book[symbol]['buy'] = next_message['buy']
            recent_book[symbol]['sell'] = next_message['sell']
            if next_message['symbol'] == "BOND":
                flip_BOND(exchange)
        elif next_message['type'] == "ack":
            trades[next_message['order_id']]['status'] = "ACK"
        elif next_message['type'] == "fill":
            order_id = next_message['order_id']
            trades[order_id]['fills'].append(next_message)
            if next_message['dir'] == "BUY":
                portfolio[symbol] += next_message["size"]
            elif next_message['dir'] == "SELL":
                portfolio[symbol] -= next_message["size"]
        elif next_message['type'] == "out":
            trades[next_message['order_id']]['status'] = "OUT"
        elif next_message['type'] == "reject":
            print(next_message)
        elif next_message['type'] == "error":
            print(next_message)
        elif next_message['type'] == "trade":
            # Don't need to do anything
            pass
        #
        # TODO: Handle server dying and restart
        #
        print("In while loop")




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
    print("flipping bond")
    for pair in recent_book['BOND']['sell']:
        if pair[0] < 1000:
            buy(exchange, "BOND", pair[0], pair[1])
    for pair in recent_book['BOND']['buy']:
        if pair[0] > 1000:
            sell(exchange, "BOND", pair[0], pair[1])


if __name__ == "__main__":
    main()
