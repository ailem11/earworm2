from flask import Flask, request, jsonify, send_from_directory
import requests
import os
import base64
import time
import hmac
import hashlib
import csv
import io
import re

import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_folder='../frontend', static_url_path='/')

# IMPORTANT: Replace with your actual ACRCloud credential
ACRCLOUD_HOST = os.environ.get('ACRCLOUD_HOST', 'identify-us-west-2.acrcloud.com')
ACRCLOUD_ACCESS_KEY = os.environ.get('ACRCLOUD_ACCESS_KEY', '')
ACRCLOUD_ACCESS_SECRET = os.environ.get('ACRCLOUD_ACCESS_SECRET', '')

http_method = 'POST'
http_uri = '/v1/identify'
data_type = "audio"
signature_version = "1"

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    try:
        # Construct a robust, absolute path to the audio directory
        dir_path = os.path.dirname(os.path.realpath(__file__))
        audio_dir = os.path.join(dir_path, 'audio')
        
        app.logger.info(f"Audio directory path: {audio_dir}")
        
        file_path = os.path.join(audio_dir, filename)
        app.logger.info(f"Attempting to serve file: {file_path}")

        if not os.path.isfile(file_path):
            app.logger.error(f"File not found at path: {file_path}")
            return jsonify({'error': 'File not found'}), 404
            
        app.logger.info(f"File found. Serving '{filename}'.")
        return send_from_directory(audio_dir, filename)
    except Exception as e:
        app.logger.error(f"An unexpected error occurred: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/identify', methods=['POST'])
def identify_song():
    if not ACRCLOUD_ACCESS_KEY or not ACRCLOUD_ACCESS_SECRET:
        app.logger.error("ACRCloud credentials are not configured in environment variables.")
        return jsonify({'error': 'ACRCloud credentials not configured on server'}), 500

    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file found'}), 400

    audio_file = request.files['audio']

    # Generate fresh timestamp and signature for this specific request
    current_timestamp = time.time()
    string_to_sign = http_method + "\n" + http_uri + "\n" + ACRCLOUD_ACCESS_KEY + "\n" + data_type + "\n" + signature_version + "\n" + str(current_timestamp)
    sign = base64.b64encode(hmac.new(
        ACRCLOUD_ACCESS_SECRET.encode('ascii'), 
        string_to_sign.encode('ascii'),
        digestmod=hashlib.sha1
    ).digest()).decode('ascii')

    files = {'sample': audio_file.read()}
    data = {
        'access_key': ACRCLOUD_ACCESS_KEY,
        'data_type': data_type,
        'sample_bytes': audio_file.content_length,
        'timestamp': str(current_timestamp),
        'signature_version': signature_version,
        'signature': sign,
    }

    # Note: ACRCloud requires a signature to be generated.
    # This is a simplified example and will not work without a proper signature.
    # You would need to implement the signature generation logic as per ACRCloud's documentation.
    # For now, this will likely return an authentication error.

    try:
        response = requests.post(f"https://{ACRCLOUD_HOST}/v1/identify", files=files, data=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Log the full JSON response for debugging
        app.logger.debug(f"ACRCloud Response: {response.json()}")
        
        return jsonify(response.json())
    except requests.exceptions.RequestException as e:
        return jsonify({'error': str(e)}), 500

def parse_sheets_id(url):
    match = re.search(r'/spreadsheets/d/(e/[a-zA-Z0-9-_]+|[a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    return None

@app.route('/stocks/portfolio', methods=['GET', 'POST'])
def get_portfolio():
    sheet_url = None
    if request.method == 'POST':
        data = request.json or {}
        sheet_url = data.get('sheetUrl')
    else:
        sheet_url = request.args.get('sheetUrl')

    demo_portfolio = [
        {"ticker": "GOOGL", "shares": 15.0, "buyPrice": 120.00},
        {"ticker": "AAPL", "shares": 10.0, "buyPrice": 150.00},
        {"ticker": "MSFT", "shares": 8.0, "buyPrice": 310.00},
        {"ticker": "TSLA", "shares": 12.0, "buyPrice": 180.00},
        {"ticker": "NVDA", "shares": 20.0, "buyPrice": 400.00}
    ]

    if not sheet_url:
        return jsonify(demo_portfolio)

    sheet_id = parse_sheets_id(sheet_url)
    if not sheet_id:
        if re.match(r'^[a-zA-Z0-9-_]+$', sheet_url):
            sheet_id = sheet_url
        else:
            return jsonify({'error': 'Invalid Google Sheets URL or ID format'}), 400

    csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/pub?output=csv"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'
    }
    
    try:
        r = requests.get(csv_url, headers=headers, timeout=10)
        if r.status_code != 200:
            csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv"
            r = requests.get(csv_url, headers=headers, timeout=10)
            
        if r.status_code == 200:
            portfolio = parse_sheets_csv(r.text)
            return jsonify(portfolio)
        else:
            return jsonify({'error': f'Failed to retrieve sheet data from Google Drive. Status: {r.status_code}'}), 400
    except Exception as e:
        app.logger.error(f"Error loading sheets portfolio: {e}")
        return jsonify({'error': str(e)}), 500

def parse_sheets_csv(csv_text):
    f = io.StringIO(csv_text)
    reader = csv.reader(f)
    rows = list(reader)
    if not rows:
        return []
    
    headers = [h.strip().lower() for h in rows[0]]
    ticker_idx = -1
    shares_idx = -1
    buy_price_idx = -1
    
    for idx, h in enumerate(headers):
        if 'ticker' in h or 'symbol' in h or 'stock' in h:
            ticker_idx = idx
        elif 'share' in h or 'qty' in h or 'quantity' in h or 'count' in h:
            shares_idx = idx
        elif ('buy' in h or 'cost' in h or 'purchase' in h or 'price' in h) and 'total' not in h:
            buy_price_idx = idx
            
    if ticker_idx == -1: ticker_idx = 0
    if shares_idx == -1: shares_idx = min(1, len(headers)-1)
    if buy_price_idx == -1: buy_price_idx = min(2, len(headers)-1)
    
    portfolio = []
    for r in rows[1:]:
        if len(r) > max(ticker_idx, shares_idx, buy_price_idx):
            ticker = r[ticker_idx].strip().upper()
            if not ticker:
                continue
            try:
                shares = float(r[shares_idx].replace(',', '').strip()) if r[shares_idx] else 1.0
                buy_price = float(r[buy_price_idx].replace('$', '').replace(',', '').strip()) if r[buy_price_idx] else 0.0
            except ValueError:
                shares = 1.0
                buy_price = 0.0
            portfolio.append({
                "ticker": ticker,
                "shares": shares,
                "buyPrice": buy_price
            })
    return portfolio

@app.route('/stocks/quotes', methods=['GET'])
def get_quotes():
    tickers_str = request.args.get('tickers', '')
    if not tickers_str:
        return jsonify({})
    
    tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
    quotes = {}
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'
    }
    
    for t in tickers:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{t}"
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                result = data.get('chart', {}).get('result', [])
                if result:
                    meta = result[0].get('meta', {})
                    current_price = meta.get('regularMarketPrice')
                    prev_close = meta.get('chartPreviousClose')
                    
                    if current_price is None:
                        indicators = result[0].get('indicators', {}).get('quote', [{}])[0]
                        closes = [c for c in indicators.get('close', []) if c is not None]
                        if closes:
                            current_price = closes[-1]
                            
                    if current_price is not None:
                        if prev_close is None:
                            prev_close = current_price
                        change = current_price - prev_close
                        change_pct = (change / prev_close) * 100 if prev_close else 0.0
                        quotes[t] = {
                            "price": round(current_price, 2),
                            "change": round(change, 2),
                            "changePercent": round(change_pct, 2)
                        }
        except Exception as e:
            app.logger.error(f"Error fetching quote for {t}: {e}")
            
    return jsonify(quotes)

@app.route('/stocks/news', methods=['GET'])
def get_news():
    ticker = request.args.get('ticker', '').strip().upper()
    if not ticker:
        return jsonify([])
        
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36'
    }
    url = f"https://query1.finance.yahoo.com/v1/finance/search?q={ticker}"
    
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            data = r.json()
            news_items = data.get('news', [])
            articles = []
            for item in news_items[:5]:
                articles.append({
                    "title": item.get('title'),
                    "publisher": item.get('publisher'),
                    "link": item.get('link'),
                    "time": item.get('providerPublishTime')
                })
            return jsonify(articles)
    except Exception as e:
        app.logger.error(f"Error fetching news for {ticker}: {e}")
        
    return jsonify([])

if __name__ == '__main__':
    # Construct absolute paths for SSL certificate and key
    dir_path = os.path.dirname(os.path.realpath(__file__))
    cert_path = os.path.join(dir_path, 'cert.pem')
    key_path = os.path.join(dir_path, 'key.pem')
    
    port = int(os.environ.get('PORT', 5001))
    
    # Check if running in Google Cloud Run (K_SERVICE is set by Cloud Run)
    is_cloud_run = os.environ.get('K_SERVICE') is not None
    has_certs = os.path.exists(cert_path) and os.path.exists(key_path)

    if has_certs and not is_cloud_run:
        app.logger.info(f"Starting Flask server with SSL on port {port}...")
        app.run(host='0.0.0.0', debug=True, port=port, ssl_context=(cert_path, key_path))
    else:
        app.logger.info(f"Starting Flask server WITHOUT SSL on port {port}...")
        app.run(host='0.0.0.0', debug=True, port=port)
