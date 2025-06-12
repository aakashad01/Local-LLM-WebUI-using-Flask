import os, json, sqlite3, requests, uuid
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from dotenv import load_dotenv
from markdown import markdown

load_dotenv()
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")
SECRET_KEY = os.getenv("SECRET_KEY", "topsecretkey")
DB_PATH = "chat.db"

app = Flask(__name__)
app.secret_key = SECRET_KEY
first_request = True

@app.before_request
def init_app():
    global first_request
    if first_request:
        init_db()
        first_request = False

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, timestamp TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS session_titles (session_id TEXT PRIMARY KEY, title TEXT)")
        conn.commit()

def save_message(session_id, role, content):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO chats (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
                  (session_id, role, content, datetime.utcnow().isoformat()))
        conn.commit()

def get_chat_history(session_id):
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT role, content, timestamp FROM chats WHERE session_id = ? ORDER BY id", (session_id,))
        return c.fetchall()

@app.route("/", methods=["GET"])
def index():
    sid = request.args.get("session_id")
    if not sid or sid == "new":
        sid = str(uuid.uuid4())
        return redirect(url_for("index", session_id=sid))
    session["session_id"] = sid

    history = get_chat_history(sid)
    formatted = [{"role": r, "content": c, "timestamp": t} for r, c, t in history]

    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("SELECT session_id FROM chats GROUP BY session_id ORDER BY MAX(timestamp) DESC")
        sessions = [row[0] for row in c.fetchall()]

    return render_template("index.html", chat=formatted, session_id=sid, all_chats=sessions)

@app.route("/send", methods=["POST"])
def send():
    data = request.json
    prompt = data["prompt"]
    sid = data.get("session_id", "default")
    save_message(sid, "user", prompt)

    def generate():
        yield ""
        response = ""
        for token in generate_response_stream(prompt):
            response += token
            yield token
        save_message(sid, "assistant", response)
    return app.response_class(generate(), mimetype="text/plain")

def generate_response_stream(prompt):
    headers = {"Content-Type": "application/json"}
    payload = {"model": MODEL_NAME, "prompt": prompt, "stream": True}
    response = requests.post(f"{OLLAMA_HOST}/api/generate", headers=headers, json=payload, stream=True)
    for chunk in response.iter_lines():
        if chunk:
            data = json.loads(chunk.decode("utf-8"))
            yield data.get("response", "")
    yield "\n"

@app.route("/rename_session")
def rename_session():
    sid = request.args.get("sid")
    name = request.args.get("name")
    if sid and name:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("INSERT OR REPLACE INTO session_titles (session_id, title) VALUES (?, ?)", (sid, name))
            conn.commit()
    return "", 204

@app.route("/delete_session")
def delete_session():
    sid = request.args.get("sid")
    if sid:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("DELETE FROM chats WHERE session_id = ?", (sid,))
            conn.execute("DELETE FROM session_titles WHERE session_id = ?", (sid,))
            conn.commit()
    return "", 204

if __name__ == "__main__":
    app.run(debug=True)
