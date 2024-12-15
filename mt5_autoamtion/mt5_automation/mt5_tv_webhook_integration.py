from flask import Flask, request, jsonify, render_template_string
import MetaTrader5 as mt5

app = Flask(__name__)

# MT5 Login Credentials
MT5_LOGIN = 190244904  # Replace with your MT5 account number
MT5_PASSWORD = "Qwerty@2"  # Replace with your MT5 password
MT5_SERVER = "Exness-MT5Trial14"  # Replace with your broker's server name

# Map received symbols to MT5-compatible symbols
SYMBOL_MAP = {
    "NAS100": "USTECm",  # Map NAS100 to USTECm
    "BTCUSD": "BTCUSDm"
    # Add more mappings as needed
}

def map_symbol(webhook_symbol):
    """Convert TradingView symbol to MT5 symbol using the mapping."""
    return SYMBOL_MAP.get(webhook_symbol, webhook_symbol)  # Default to the same symbol if no mapping exists

# Initialize and login to MT5
def init_mt5():
    if not mt5.initialize():
        return "MT5 Initialization failed"

    authorized = mt5.login(MT5_LOGIN, password=MT5_PASSWORD, server=MT5_SERVER)
    if not authorized:
        return f"MT5 Login failed: {mt5.last_error()}"
    return "MT5 Login successful"


@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json

        if not data:
            print("Error: No JSON payload received")
            return jsonify({"status": "error", "message": "No JSON payload received"}), 400

        print("Received alert:", data)

        action = data['action'].lower()
        symbol = data['symbol']
        mt5_symbol = map_symbol(symbol)

        try:
            price = float(data['price'])
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid price format"}), 400

        if not action or not symbol or not price:
            print("Error: Missing required fields in payload")
            return jsonify({"status": "error", "message": "Missing fields in payload"}), 400

        if action == 'buy':
            response = place_mt5_order(mt5_symbol, mt5.ORDER_TYPE_BUY, price)
        elif action == 'sell':
            response = place_mt5_order(mt5_symbol, mt5.ORDER_TYPE_SELL, price)
        else:
            print("Error: Invalid action")
            return jsonify({"status": "error", "message": "Invalid action"}), 400

        # Return the response from the order placement
        if response["status"] == "success":
            return jsonify({"status": "success", "message": response["message"]}), 200
        else:
            return jsonify({"status": "error", "message": response["message"]}), 500

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


def place_mt5_order(symbol, order_type, price=None):
    login_status = init_mt5()
    if "failed" in login_status:
        print(login_status)
        return {"status": "error", "message": login_status}

    # Verify symbol exists
    if not mt5.symbol_select(symbol, True):
        print(f"Symbol {symbol} not found")
        return {"status": "error", "message": f"Symbol {symbol} not found"}

    # Fetch latest market price if price is not provided
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        print(f"Failed to get tick data for {symbol}")
        return {"status": "error", "message": f"Failed to get tick data for {symbol}"}

    # Set price dynamically
    if order_type == mt5.ORDER_TYPE_BUY:
        price = tick.ask  # Buy at ask price
    elif order_type == mt5.ORDER_TYPE_SELL:
        price = tick.bid  # Sell at bid price

    # Prepare order request
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": 0.01,  # Adjust volume based on broker requirements
        "type": order_type,
        "price": price,
        "deviation": 20,
        "magic": 234000,
        "comment": "TradingView Alert",
        "type_filling": mt5.ORDER_FILLING_IOC,
        "type_time": mt5.ORDER_TIME_GTC,
    }
    print(request)
    # Send the order
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed: {result}")
        return {"status": "error", "message": f"Order failed: {result.comment}"}
    else:
        print("Order placed successfully")
        return {"status": "success", "message": "Order placed successfully"}



# New Route for Logging in and Fetching Balance
@app.route('/login_balance', methods=['GET'])
def login_balance():
    login_status = init_mt5()

    if "failed" in login_status:
        return f"<h1>{login_status}</h1>"

    account_info = mt5.account_info()
    if account_info is None:
        return "<h1>Login failed, check credentials</h1>"

    # Render the account balance
    return render_template_string(
        """
        <h1>MT5 Account Balance</h1>
        <ul>
            <li>Account Name: {{ account_info.name }}</li>
            <li>Account Balance: {{ account_info.balance }}</li>
            <li>Account Equity: {{ account_info.equity }}</li>
            <li>Account Currency: {{ account_info.currency }}</li>
        </ul>
        """,
        account_info=account_info
    )

if __name__ == '__main__':
    app.run(port=5000, debug=True)
