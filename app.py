
import os
from flask import Flask, request, jsonify, abort, render_template
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



# Main index page route
@app.route('/')
def index():
    return render_template('index.html', title='Welcome to ZOPHOS')


# Docs page route using Jinja2 template
@app.route('/docs')
def docs():
    return render_template('docs.html', title='Documentation')

# Features page route
@app.route('/features')
def features():
    return render_template('features.html', title='Features')

# Community page route
@app.route('/community')
def community():
    return render_template('community.html', title='Community')

# Dashboard page route
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html', title='Bot Dashboard')


# Home page route
@app.route('/home')
def home_page():
    return render_template('home.html', title='Home')

# Profile/account-related routes
@app.route('/settings')
def settings():
    return render_template('account/settings.html', title='Settings')

@app.route('/account/plan')
def account_plan():
    return render_template('account/plan.html', title='Account Plan')

@app.route('/admin')
def admin():
    return render_template('admin.html', title='Admin')

@app.route('/approvals')
def approvals():
    return render_template('approvals.html', title='Approvals')

@app.route('/help')
def help_page():
    return render_template('account/help.html', title='Help Center')

@app.route('/signin')
def signin():
    return render_template('signin.html', title='Sign In')

@app.route('/signup')
def signup():
    return render_template('account/signup.html', title='Sign Up')

if __name__ == '__main__':
    app.run(debug=True)
