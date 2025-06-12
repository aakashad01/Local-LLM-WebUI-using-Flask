import os
import json
import sqlite3
import requests
import uuid
from datetime import datetime
from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session
)
from dotenv import load_dotenv

# ─── Load environment ──────────────────────────────────────────────────────────
load_dotenv()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME  = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
SECRET_KEY  = os.getenv("SECRET_KEY", "change_this_to_a_real_secret")
DB_PATH     = "chat.db"

# ─── App Setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = SECRET_KEY   # ← Set your secret key here

# ─── One-time DB initialization ────────────────────────────────────────────────
first_request = True

@app.before_request
def init_app():
    global first_request
    if first_request:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    timestamp TEXT
                )
            ''')
        print("✅ Database initialized.")
        first_request = False

# ─── Database helpers ─────────────────────────────────────────────────────────
def save_message(session_id, role, content):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO chats (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, role, content, datetime.utcnow().isoformat())
        )

def get_chat_history(session_id):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute(
            "SELECT role, content, timestamp FROM chats "
            "WHERE session_id = ? ORDER BY id",
            (session_id,)
        )
        return cur.fetchall()

# ─── Ollama streaming ──────────────────────────────────────────────────────────
def generate_response_stream(prompt):
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": True
    }
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        headers={"Content-Type": "application/json"},
        json=payload,
        stream=True
    )
    full = ""
    for line in resp.iter_lines():
        if not line:
            continue
        data = json.loads(line.decode())
        token = data.get("response", "")
        full += token
        yield token
    yield "\n"  # end
    return full

# ─── Routes ────────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def index():
    sid = request.args.get("session_id")

    # Create or renew session
    if not sid or sid == "new":
        new_sid = str(uuid.uuid4())
        return redirect(url_for("index", session_id=new_sid))

    session["session_id"] = sid

    # Load history
    raw = get_chat_history(sid)
    history = [
        {"role": role, "content": content, "timestamp": ts}
        for role, content, ts in raw
    ]

    # Sidebar list
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT DISTINCT session_id FROM chats"
        ).fetchall()
    all_chats = [r[0] for r in rows]

    return render_template(
        "index.html",
        chat=history,
        session_id=sid,
        all_chats=all_chats
    )

@app.route("/send", methods=["POST"])
def send():
    data = request.get_json()
    prompt = data["prompt"]
    sid = data.get("session_id", session.get("session_id", "default"))

    # Save user message
    save_message(sid, "user", prompt)

    def generate():
        response_accum = ""
        for token in generate_response_stream(prompt):
            response_accum += token
            yield token
        # Save assistant reply
        save_message(sid, "assistant", response_accum)

    return app.response_class(generate(), mimetype="text/plain")

@app.route("/chats", methods=["GET"])
def list_chats():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT DISTINCT session_id FROM chats"
        ).fetchall()
    return jsonify([r[0] for r in rows])
@app.route("/rename_session", methods=["POST"])
def rename_session():
    data = request.json
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE chats SET title = ? WHERE session_id = ?", (data["new_title"], data["session_id"]))
    return jsonify(status="ok")

@app.route("/delete_session", methods=["POST"])
def delete_session():
    data = request.json
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("DELETE FROM chats WHERE session_id = ?", (data["session_id"],))
    return jsonify(status="deleted")

# ─── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True)
