from flask import Flask, request, jsonify
import ast
import operator
import os
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


def to_number(value):
    """Return int if whole number, otherwise float."""
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return value


@app.route('/')
def index():
    # --- queryEval ---
    expr = request.args.get('queryEval')
    if expr is not None:
        try:
            result = safe_eval(expr)
            return jsonify(to_number(result))
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    # --- queryStockPrice ---
    ticker = request.args.get('queryStockPrice')
    if ticker is not None:
        try:
            api_key = os.environ.get('ALPHA_VANTAGE_KEY')
            url = (
                f"https://www.alphavantage.co/query"
                f"?function=GLOBAL_QUOTE&symbol={ticker}&apikey={api_key}"
            )
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            quote = data.get('Global Quote', {})
            price = quote.get('05. price')
            if not price:
                return jsonify({"error": f"Ticker not found: {ticker}"}), 404
            return jsonify(to_number(float(price)))
        except Exception as e:
            return jsonify({"error": str(e)}), 400

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
                return jsonify({"error": f"Airport not found: {iata}"}), 404
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
            return jsonify(to_number(temp))
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    return jsonify({"usage": "Use queryEval, queryStockPrice, or queryAirportTemp parameters."})
