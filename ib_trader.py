from ib.opt import Connection, message
from ib.ext.Contract import Contract
from ib.ext.Order import Order

ibConnection = None

def watchAll(msg):
    print(msg)

def operate(orderId, ticker, action, quantity, price=None):
    """"""
    # 1. get contrat
    print("Building Contract...")
    contract = Contract()
    contract.m_symbol = ticker
    contract.m_secType = 'STK'
    contract.m_exchange = 'NASDAQ'
    contract.m_currency = 'USD'
    print(ibConnection.reqMktData(1,contract,"",False))
    # 2. Order
    order = Order()
    if price is not None:
        order.m_orderType = 'LMT'
        order.m_lmtPrice = price
    else:
        order.m_orderType = 'MKT'

    order.m_totalQuantity = quantity
    order.m_action = action
    # .3. Place Order
    print("Placing Order...")
    ibConnection.placeOrder(orderId, contract, order)
    print("Order placed")

# Step 1. Establish connection
ibConnection = Connection.create(port=7497, clientId=999)
ibConnection.connect()
# Step 2. SHORT SELL AT MKT ORDER FOR TVIX 20
operate(orderId=12, ticker="TSLA", action='BUY', quantity=10)
# Setp 3. Disconnect
ibConnection.disconnect()
