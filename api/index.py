from flask import Flask, request
import ast
import operator
import requests

app = Flask(__name__)


def safe_eval(expr):
    """Safely evaluate arithmetic expressions using AST parsing."""
    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.USub: operator.neg,
        ast.UAdd: operator.pos,
    }

    def _eval(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        elif isinstance(node, ast.BinOp):
            return ops[type(node.op)](_eval(node.left), _eval(node.right))
        elif isinstance(node, ast.UnaryOp):
            return ops[type(node.op)](_eval(node.operand))
        else:
            raise ValueError(f"Unsupported expression node: {type(node).__name__}")

    tree = ast.parse(expr, mode='eval')
    return _eval(tree.body)


def format_number(value):
    """Return int string if whole number, otherwise float string."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


@app.route('/')
def index():
    # --- queryEval ---
    expr = request.args.get('queryEval')
    if expr is not None:
        try:
            result = safe_eval(expr)
            return format_number(result)
        except Exception as e:
            return f"Error evaluating expression: {e}", 400

    # --- queryStockPrice ---
    ticker = request.args.get('queryStockPrice')
    if ticker is not None:
        try:
            url = (
                f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
                "?interval=1d&range=1d"
            )
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                )
            }
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            price = data['chart']['result'][0]['meta']['regularMarketPrice']
            return format_number(price)
        except Exception as e:
            return f"Error fetching stock price: {e}", 400

    # --- queryAirportTemp ---
    iata = request.args.get('queryAirportTemp')
    if iata is not None:
        try:
            # Step 1: get airport coordinates
            airport_resp = requests.get(
                f"https://airport-data.com/api/ap_info.json?iata={iata}",
                timeout=10,
            )
            airport_resp.raise_for_status()
            airport = airport_resp.json()
            if airport.get('status') == 404 or 'latitude' not in airport:
                return f"Airport not found: {iata}", 404
            lat = airport['latitude']
            lon = airport['longitude']

            # Step 2: get current temperature from Open-Meteo (free, no key)
            weather_resp = requests.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    'latitude': lat,
                    'longitude': lon,
                    'current_weather': 'true',
                },
                timeout=10,
            )
            weather_resp.raise_for_status()
            weather = weather_resp.json()
            temp = weather['current_weather']['temperature']
            return format_number(temp)
        except Exception as e:
            return f"Error fetching airport temperature: {e}", 400

    return (
        "Usage:\n"
        "  /?queryEval=10+(5*2)\n"
        "  /?queryStockPrice=AAPL\n"
        "  /?queryAirportTemp=PRG\n"
    )
