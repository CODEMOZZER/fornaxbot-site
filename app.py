import os
from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# CockroachDB connection settings (replace with your credentials)
DB_URL = os.getenv('DB_URL','postgresql://zamozzer:4bqveY60lK8Vduv1oC6mig@lowerdiscordbotallinone-10666.jxf.cockroachlabs.cloud:26257/zophos-site?sslmode=verify-full&sslrootcert=/home/codespace/.postgresql/root.crt')

conn = psycopg2.connect(DB_URL, cursor_factory=RealDictCursor)

# Forum table setup (run once in CockroachDB)
# CREATE TABLE IF NOT EXISTS forum_messages (
#   id SERIAL PRIMARY KEY,
#   username VARCHAR(64),
#   role VARCHAR(16),
#   message TEXT,
#   created_at TIMESTAMPTZ DEFAULT now()
# );

@app.route('/api/messages', methods=['GET'])
def get_messages():
    with conn.cursor() as cur:
        cur.execute('SELECT * FROM forum_messages ORDER BY created_at DESC LIMIT 50;')
        messages = cur.fetchall()
    return jsonify(messages)

@app.route('/api/messages', methods=['POST'])
def post_message():
    data = request.json
    username = data.get('username', 'Anonymous')
    role = data.get('role', 'Member')
    message = data.get('message', '')
    if not message:
        return jsonify({'error': 'Message required'}), 400
    with conn.cursor() as cur:
        cur.execute('INSERT INTO forum_messages (username, role, message) VALUES (%s, %s, %s) RETURNING id;',
                    (username, role, message))
        conn.commit()
        msg_id = cur.fetchone()['id']
    return jsonify({'id': msg_id, 'username': username, 'role': role, 'message': message})

@app.route('/api/messages/<int:msg_id>', methods=['DELETE'])
def delete_message(msg_id):
    # Basic owner authentication (replace with real auth in production)
    token = request.headers.get('X-Owner-Token')
    if token != os.getenv('OWNER_TOKEN', 'changeme'):
        return jsonify({'error': 'Unauthorized'}), 403
    with conn.cursor() as cur:
        cur.execute('DELETE FROM forum_messages WHERE id = %s;', (msg_id,))
        conn.commit()
    return jsonify({'success': True})

# Chat endpoints must be at top level
@app.route('/api/chat', methods=['GET'])
def get_chat_messages():
    with conn.cursor() as cur:
        # Delete messages older than 30 days
        cur.execute("DELETE FROM chat_messages WHERE timestamp < now() - INTERVAL '30 days';")
        conn.commit()
        # Fetch recent messages
        cur.execute('SELECT * FROM chat_messages ORDER BY timestamp DESC LIMIT 50;')
        messages = cur.fetchall()
    return jsonify(messages)

@app.route('/api/chat', methods=['POST'])
def post_chat_message():
    data = request.json
    username = data.get('username', 'Anonymous')
    message = data.get('message', '')
    if not message:
        return jsonify({'error': 'Message required'}), 400
    with conn.cursor() as cur:
        cur.execute('INSERT INTO chat_messages (username, message) VALUES (%s, %s) RETURNING id;',
                    (username, message))
        conn.commit()
        msg_id = cur.fetchone()['id']
    return jsonify({'id': msg_id, 'username': username, 'message': message})

# Homepage route with site colors and centered text
@app.route('/')
def home():
    return '''
    <html>
    <head>
        <title>Zophos - Home</title>
        <style>
            body {
                margin: 0;
                font-family: 'Roboto', Arial, sans-serif;
                background: radial-gradient(ellipse at center, #10131a 60%, #05060a 100%);
                color: #eaf6ff;
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .center-box {
                background: #181a24;
                border-radius: 12px;
                padding: 48px 64px;
                box-shadow: 0 2px 12px 0 rgba(0, 170, 255, 0.15);
                text-align: center;
            }
            h1 {
                color: #00cfff;
                font-size: 2.5em;
                margin-bottom: 18px;
            }
            p {
                font-size: 1.2em;
                color: #eaf6ff;
            }
        </style>
    </head>
    <body>
        <div class="center-box">
            <h1>Welcome to Zophos!</h1>
            <p>Your community site and chat API are running.<br>Visit <b>/community.html</b> to join the chat.</p>
        </div>
    </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(debug=True)
