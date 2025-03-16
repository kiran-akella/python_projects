import yaml
from flask import Flask, request, jsonify
from flask_httpauth import HTTPBasicAuth

app = Flask(__name__)
auth = HTTPBasicAuth()

# File paths
DATA_FILE = 'data.yaml'
USERS_FILE = 'users.yaml'

# Function to load data from the YAML file
def load_data():
    try:
        with open(DATA_FILE, 'r') as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        return {}

# Function to save data to the YAML file
def save_data(data):
    with open(DATA_FILE, 'w') as file:
        yaml.dump(data, file)

# Function to load users and passwords from the users YAML file
def load_users():
    try:
        with open(USERS_FILE, 'r') as file:
            return yaml.safe_load(file) or {}
    except FileNotFoundError:
        return {}

# Basic authentication callback
@auth.verify_password
def verify_password(username, password):
    users = load_users()  # Load users from users.yaml file
    if username in users and users[username] == password:
        return username
    return None

# GET method - Retrieve a value by key
@app.route('/data/<key>', methods=['GET'])
@auth.login_required
def get_data(key):
    data_store = load_data()
    if key in data_store:
        return jsonify({key: data_store[key]}), 200
    else:
        return jsonify({"error": "Key not found"}), 404

# POST method - Add a new key-value pair
@app.route('/data', methods=['POST'])
@auth.login_required
def post_data():
    content = request.json  # Get the data in JSON format
    if 'key' not in content or 'value' not in content:
        return jsonify({"error": "Key and value are required"}), 400
    
    key = content['key']
    value = content['value']
    
    data_store = load_data()
    
    if key in data_store:
        return jsonify({"error": "Key already exists"}), 400

    data_store[key] = value
    save_data(data_store)
    return jsonify({"message": "Data added successfully"}), 201

# PUT method - Update the value for an existing key
@app.route('/data/<key>', methods=['PUT'])
@auth.login_required
def update_data(key):
    data_store = load_data()
    if key not in data_store:
        return jsonify({"error": "Key not found"}), 404
    
    content = request.json
    if 'value' not in content:
        return jsonify({"error": "Value is required"}), 400
    
    data_store[key] = content['value']
    save_data(data_store)
    return jsonify({"message": "Data updated successfully"}), 200

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=5000, debug=True, threaded=True)
