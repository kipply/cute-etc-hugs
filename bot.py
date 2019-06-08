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
test_exchange_index = 1
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
offering = {
    u'BOND': {'BUY': 0, 'SELL': 0, 'PENDING_BUY': 0, 'PENDING_SELL': 0},
    u'VALBZ': {'BUY': 0, 'SELL': 0, 'PENDING_BUY': 0, 'PENDING_SELL': 0},
    u'VALE': {'BUY': 0, 'SELL': 0, 'PENDING_BUY': 0, 'PENDING_SELL': 0, 'CONVERT': 0},
    u'GS': {'BUY': 0, 'SELL': 0, 'PENDING_BUY': 0, 'PENDING_SELL': 0},
    u'MS': {'BUY': 0, 'SELL': 0, 'PENDING_BUY': 0, 'PENDING_SELL': 0},
    u'WFC': {'BUY': 0, 'SELL': 0, 'PENDING_BUY': 0, 'PENDING_SELL': 0},
    u'XLF': {'BUY': 0, 'SELL': 0, 'PENDING_BUY': 0, 'PENDING_SELL': 0, 'CONVERT': 0},
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
    for symb in hello_from_exchange['symbols']:
      portfolio[symb['symbol']] = symb['position']

    oben = portfolio["VALE"] - portfolio["VALBZ"]
    if(oben > 0):
        if portfolio["VALE"] > 5:
            convert(exchange, "VALE", 'SELL', portfolio["VALE"])
    if(oben < 0):
        if portfolio["VALE"] < -5:
            print ("REEEEEEEEE!")
            convert(exchange, "VALE", 'BUY', -portfolio["VALE"])

    while True:
        next_message = read_from_exchange(exchange)

        # print("\nNext message = ", next_message, "\n")
        extra_log.write(str(next_message))
        if next_message['type'] == "book":
            symbol = next_message['symbol']
            recent_book[symbol]['buy'] = next_message['buy']
            recent_book[symbol]['sell'] = next_message['sell']
            if next_message['symbol'] == "BOND":
                flip_BOND(exchange)
            if next_message['symbol'] == "VALBZ" or next_message['symbol'] == "VALE":
                adrArbitrage(exchange)
            if next_message['symbol'] == "VALBZ":
                for id, trad in enumerate(trades):
                    if trad['symbol'] == "VALE" and trad['status'] == "ACK":
                      try:
                        if trad['dir'] == "BUY" and trad['price'] >= next_message['sell'][0][0] - 3:
                            cancel(exchange,id)
                        elif trad['dir'] == "SELL" and trad['price'] <= next_message['buy'][0][0] + 3:
                            cancel(exchange,id)
                      except: pass

        elif next_message['type'] == "ack":
            offer = trades[next_message['order_id']]
            if(offer['type'] == "trade"):
                offer['status'] = "ACK"
                offering[offer['symbol']]['PENDING_' + offer['dir']] -= offer['size']
                offering[offer['symbol']][offer['dir']] += offer['size']
            if(offer['type'] == "convert"):
                unit = 1
                if (offer['dir'] == "SELL"):
                    unit = -1

                portfolio[offer['symbol']] += offer['size'] * unit
                if(offer['symbol'] == "VALE"):
                    portfolio["VALBZ"] -= offer['size'] * unit
                if(offer['symbol'] == "XLF"):
                    portfolio["BOND"] -= 0.3 * offer['size'] * unit
                    portfolio["GS"] -= 0.2 * offer['size'] * unit
                    portfolio["MS"] -= 0.3 * offer['size'] * unit
                    portfolio["WFC"] -= 0.2 * offer['size'] * unit
            print("ACK:", offer['dir'], offer['price'], offer['size'])
            print("Offering[BOND]:", offering['BOND'])

        elif next_message['type'] == "fill":
            offer = trades[next_message['order_id']]
            offer['fills'].append(next_message)
            if next_message['dir'] == "BUY":
                portfolio[offer['symbol']] += next_message["size"]
            elif next_message['dir'] == "SELL":
                portfolio[offer['symbol']] -= next_message["size"]
            if symbol == "VALE":
                #close position
                oben = portfolio["VALE"] + portfolio["VALBZ"]
                if(oben > 0):
                    sell(exchange, "VALBZ", recent_book["VALBZ"]['buy'][0], oben)
                    if portfolio["VALE"] > 4:
                        convert(exchange, "VALE", 'SELL', portfolio["VALE"])
                if(oben < 0):
                    buy(exchange, "VALBZ", recent_book["VALBZ"]['sell'][0], -oben)
                    if portfolio["VALE"] < -4:
                        print ("REEEEEEEEE!")
                        convert(exchange, "VALE", 'BUY', -portfolio["VALE"])
            portfolio[offer['symbol']] -= next_message["size"]
            offering[offer['symbol']][offer['dir']] -= next_message['size']
            print("Filled")
            print(next_message)
            # print("Offering[BOND]:", offering['BOND'])

        elif next_message['type'] == "out":
            trades[next_message['order_id']]['status'] = "OUT"
            if trades[next_message['order_id']]['symbol'] == "VALE" or trades[next_message['order_id']]['symbol'] == "VALBZ":
              print(next_message, "OUT")
            trades[next_message['order_id']]['status'] = "OUT"
            print(bcolors.WARNING + "OUT" + bcolors.ENDC)
        elif next_message['type'] == "reject":
            print(trades[next_message['order_id']])
            print(next_message)
            offer = trades[next_message['order_id']]
            offering[offer['symbol']]['PENDING_' + offer['dir']] -= offer['size']
            print("Rejected:", offer['dir'], offer['price'], offer['size'], "Reason:", next_message['error'])
        elif next_message['type'] == "error":
            print("Trade error!")
        elif next_message['type'] == "trade":
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

        # if offering['BOND']['SELL'] + offering['BOND']['PENDING_SELL'] < 100 + portfolio['BOND']:
        #     print("(FS) Portfolio:", portfolio["BOND"], "Offering:", offering['BOND'])
        #     sell(exchange, "BOND", 1001, 100 + portfolio['BOND'] -
        #          offering['BOND']['SELL'] - offering['BOND']['PENDING_SELL'])
        # if offering['BOND']['BUY'] + offering['BOND']['PENDING_BUY'] < 100 - portfolio['BOND']:
        #     print("(FS) Portfolio:", portfolio["BOND"], "Offering:", offering['BOND'])
        #     buy(exchange, "BOND", 999, 100 - portfolio['BOND'] -
        #         offering['BOND']['BUY'] - offering['BOND']['PENDING_BUY'])

        # TODO: Handle server dying and restart


def buy(exchange, name, price, size):
    print("trying to buy", name, price, size)
    write_to_exchange(exchange, {
        'type': 'add',
        'order_id': ID(),
        'symbol': name,
        'dir': 'BUY',
        'price': price,
        'size': size
    })
    trades.append({
        'type' : "trade",
        'symbol': name,
        'price': price,
        'size': size,
        'status': 'SENT',
        'dir': 'BUY',
        'fills': []
    })
    offering[name]['PENDING_BUY'] += size


def sell(exchange, name, price, size):
    print("trying to sell", name, price, size)
    write_to_exchange(exchange, {
        'type': 'add',
        'order_id': ID(),
        'symbol': name,
        'dir': 'SELL',
        'price': price,
        'size': size
    })
    trades.append({
        'type': "trade",
        'symbol': name,
        'price': price,
        'size': size,
        'status': 'SENT',
        'dir': 'SELL',
        'fills': []
    })
    offering[name]['PENDING_SELL'] += size


def convert(exchange, name, dir, size):
    print("trying_to_convert", name, dir, size)
    write_to_exchange(exchange, {
        'type': 'convert',
        'order_id' : ID(),
        'symbol' : name,
        'dir' : dir,
        'size' : size
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

def cancel(exchange, ID):
    write_to_exchange(exchange, {
        'type': 'cancel',
        'order_id': ID
    })

def flip_BOND(exchange):
    return
    # for pair in recent_book['BOND']['sell']:
    #     if pair[0] < 1000:
    #         buy(exchange, "BOND", pair[0], pair[1])
    # for pair in recent_book['BOND']['buy']:
    #     if pair[0] > 1000:
    #         sell(exchange, "BOND", pair[0], pair[1])
def maxBuyVA(name):
    return 10 - portfolio[name] - offering[name]['BUY'] - offering[name]["PENDING_BUY"]
def maxSellVA(name):
    return 10 + portfolio[name] - offering[name]['SELL'] - offering[name]["PENDING_SELL"]
def adrArbitrage(exchange):

    try:
      sellEstimate = recent_book["VALBZ"]['sell'][0]
    except:
      return
    # volume = sellEstimate[1]
    # for pair in recent_book["VALE"]['buy']:
    #     if pair[0] > sellEstimate[0] and volume > 0:
    #         sell(exchange, "VALE", pair[0], min(pair[1], volume))
    #         buy(exchange, "VALBZ", sellEstimate[0], min(pair[1], volume))
    #         convert(exchange, "VALE", "BUY", min(pair[1], volume))
    #         print("Attempt SELL BUY CONVERT VALE/VALBZ/VARE")
    #         volume -= min(pair[1], volume)
    try:
      if recent_book["VALE"]['sell'][0] > sellEstimate[0] + 3:
          if(maxSellVA("VALE") > 0):
              sell(exchange, "VALE", sellEstimate[0] + 3, maxSellVA("VALE"))
              print("Attempt sell VALE", maxSellVA("VALE"))
    except: print(recent_book["VALE"]['sell'])
    try:
      buyEstimate = recent_book["VALBZ"]['buy'][0]
    except:
      return
    # volumeBuy = buyEstimate[1]
    # for pair in recent_book["VALE"]['sell']:
    #     if pair[0] < buyEstimate[0] and volume > 0:
    #         buy(exchange, "VALE", pair[0], min(pair[1], volumeBuy))
    #         sell(exchange, "VALBZ", buyEstimate[0], min(pair[1], volumeBuy))
    #         convert(exchange, "VALE", 'SELL', min(pair[1], volumeBuy))
    #         print("Attempt SELL BUY CONVERT VALE/VALBZ/VARE")
    #         volumeBuy -= min(pair[1], volumeBuy)
    try:
      if recent_book["VALE"]['buy'][0] < buyEstimate[0] - 3:
          if(maxBuyVA("VALE") > 0):
              buy(exchange, "VALE", buyEstimate[0] - 3, maxBuyVA("VALE"))
              print("Attempt ADR buy VALE")
    except:
      return


#def adrPenny(exchange):
    #print("adrPenny")
    #for

if __name__ == "__main__":
    main()
