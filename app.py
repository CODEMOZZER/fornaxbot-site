
from flask import Flask, render_template
from datetime import datetime

app = Flask(__name__)

@app.context_processor
def inject_globals():
    return {"current_year": datetime.utcnow().year}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/features")
def features():
    return render_template("features.html")

@app.route("/docs")
def docs():
    return render_template("docs.html")

@app.route("/community")
def community():
    return render_template("community.html")

@app.route("/profile")
def profile():
    return render_template("profile.html")

@app.route("/health")
def health():
    return {"status": "ok"}

@app.route("/signin")
def signin():
    return render_template("signin.html")

@app.route("/signup")
def signup():
    return render_template("signup.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
