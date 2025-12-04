
import os
from flask import Flask, request, jsonify, abort
from collections import defaultdict
import time
# Basic in-memory rate limiting (per IP, per endpoint)
rate_limit_window = 60  # seconds
rate_limit_max_requests = 10
rate_limit_data = defaultdict(list)

def check_rate_limit(endpoint):
    ip = request.remote_addr
    now = time.time()
    window_start = now - rate_limit_window
    # Remove old requests
    rate_limit_data[(ip, endpoint)] = [t for t in rate_limit_data[(ip, endpoint)] if t > window_start]
    if len(rate_limit_data[(ip, endpoint)]) >= rate_limit_max_requests:
        abort(429, description="Rate limit exceeded. Please try again later.")
    rate_limit_data[(ip, endpoint)].append(now)
import psycopg2
from psycopg2.extras import RealDictCursor
from flask_cors import CORS



app = Flask(__name__)
CORS(app, origins=[
    "https://zophos-site-production.up.railway.app",
    "https://www.zophos.dedyn.io",
    "https://your-infinityfree-domain.com"
])  # Restrict CORS to trusted domains

# Generic error handler
@app.errorhandler(Exception)
def handle_error(e):
    code = getattr(e, 'code', 500)
    if code == 429:
        return jsonify({'error': 'Rate limit exceeded. Please try again later.'}), 429
    return jsonify({'error': 'An unexpected error occurred.'}), code

# CockroachDB connection settings (replace with your credentials)

DB_URL = os.getenv('DB_URL','postgresql://zamozzer:4bqveY60lK8Vduv1oC6mig@lowerdiscordbotallinone-10666.jxf.cockroachlabs.cloud:26257/zophos-site?sslmode=verify-full&sslrootcert=/home/codespace/.postgresql/root.crt')
print("DB_URL:", DB_URL)
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


# Banned words filter (expand as needed)
BANNED_WORDS = {
    "spam", "badword1", "badword2", "offensive1", "offensive2", "curse1", "curse2",
    "hate", "racist", "sexist", "homophobic", "transphobic", "violent", "threat", "bully"
}


# In-memory warning/block tracking (per IP)
user_warnings = defaultdict(int)
blocked_ips = set()
# Track terms agreement per IP
agreed_ips = set()

# Endpoint to check if current IP has agreed to terms
@app.route('/api/terms/agreed', methods=['GET'])
def check_terms_agreed():
    ip = request.remote_addr
    return jsonify({'agreed': ip in agreed_ips})

# Endpoint to record agreement for current IP
@app.route('/api/terms/agreed', methods=['POST'])
def set_terms_agreed():
    ip = request.remote_addr
    agreed_ips.add(ip)
    return jsonify({'agreed': True})

@app.route('/api/chat', methods=['POST'])
def post_chat_message():
    check_rate_limit('/api/chat')
    ip = request.remote_addr
    data = request.json
    username = data.get('username', 'Anonymous')
    message = data.get('message', '')
    agreed_to_terms = data.get('agreedToTerms', None)

    # Block if IP is blocked
    if ip in blocked_ips:
        return jsonify({'error': 'You are blocked from posting due to repeated violations.'}), 403

    # Block if user disagreed with terms
    if agreed_to_terms == 'no':
        blocked_ips.add(ip)
        return jsonify({'error': 'You must agree to the terms to participate.'}), 403

    violation = None
    if not message:
        violation = 'Message required'
    elif len(message) > 256:
        violation = 'Message too long (max 256 characters).'
    elif any(bad in message.lower() for bad in BANNED_WORDS):
        violation = 'Message contains inappropriate content.'

    if violation:
        user_warnings[ip] += 1
        if user_warnings[ip] >= 3:
            blocked_ips.add(ip)
            return jsonify({'error': f'You are blocked after 3 violations: {violation}', 'blocked': True}), 403
        return jsonify({'error': violation, 'warning_count': user_warnings[ip], 'blocked': False}), 400

    with conn.cursor() as cur:
        cur.execute('INSERT INTO chat_messages (username, message) VALUES (%s, %s) RETURNING id;',
                    (username, message))
        conn.commit()
        msg_id = cur.fetchone()['id']
    return jsonify({'id': msg_id, 'username': username, 'message': message, 'warning_count': user_warnings[ip], 'blocked': False})

# Manual moderation endpoint (delete message by id, owner token required)
@app.route('/api/chat/<int:msg_id>', methods=['DELETE'])
def delete_chat_message(msg_id):
    token = request.headers.get('X-Owner-Token')
    if token != os.getenv('OWNER_TOKEN', 'changeme'):
        return jsonify({'error': 'Unauthorized'}), 403
    with conn.cursor() as cur:
        cur.execute('DELETE FROM chat_messages WHERE id = %s;', (msg_id,))
        conn.commit()
    return jsonify({'success': True})

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
