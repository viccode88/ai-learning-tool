from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 允許 React 訪問 API

@app.route('/api/message', methods=['GET'])
def get_message():
    return jsonify({"message": "Hello from Flask!"})

if __name__ == '__main__':
    app.run(debug=True, port=5000)  # Flask 監聽 5000 端口
