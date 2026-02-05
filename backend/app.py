from flask import Flask, request, jsonify, send_from_directory
import requests
import os
import base64
import time
import hmac
import hashlib

import logging

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__, static_folder='../frontend', static_url_path='/')

# IMPORTANT: Replace with your actual ACRCloud credential
ACRCLOUD_HOST = os.environ.get('ACRCLOUD_HOST', 'identify-us-west-2.acrcloud.com')
ACRCLOUD_ACCESS_KEY = os.environ.get('ACRCLOUD_ACCESS_KEY', 'd98c2be2402228bbd0746524b5ab82fb')
ACRCLOUD_ACCESS_SECRET = os.environ.get('ACRCLOUD_ACCESS_SECRET', 'oQPXlgdNldryLGl4sIfz9V0g6997MZSZnVnB3eUn')


http_method = 'POST'
http_uri = '/v1/identify'
data_type = "audio"
signature_version = "1"
timestamp = time.time()

string_to_sign = http_method + "\n" + http_uri + "\n" + ACRCLOUD_ACCESS_KEY + "\n" + data_type + "\n" + signature_version + "\n" + str(
    timestamp)
sign = base64.b64encode(hmac.new(ACRCLOUD_ACCESS_SECRET.encode('ascii'), string_to_sign.encode('ascii'),
                                 digestmod=hashlib.sha1).digest()).decode('ascii')

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
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file found'}), 400

    audio_file = request.files['audio']

    files = {'sample': audio_file.read()}
    data = {
        'access_key': ACRCLOUD_ACCESS_KEY,
        'data_type': data_type,
        'sample_bytes': audio_file.content_length,
        'timestamp': str(timestamp), # This can be improved with actual timestamps
        'signature_version': signature_version,
        'signature': sign, # This needs to be generated
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

if __name__ == '__main__':
    # Construct absolute paths for SSL certificate and key
    dir_path = os.path.dirname(os.path.realpath(__file__))
    cert_path = os.path.join(dir_path, 'cert.pem')
    key_path = os.path.join(dir_path, 'key.pem')
    
    app.run(host='0.0.0.0', debug=True, port=5001, ssl_context=(cert_path, key_path))
