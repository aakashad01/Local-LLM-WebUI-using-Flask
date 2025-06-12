from flask import Flask

app = Flask(__name__)

# Flag to track first request
first_request = True

@app.before_request
def before_first_request():
    global first_request
    if first_request:
        print("🚀 One-time app initialization here (e.g., DB load, model warm-up)")
        # 🔧 Add your one-time setup here
        # Example: load_chat_history(), connect_to_db(), etc.
        first_request = False

@app.route("/")
def home():
    return "✅ App is running and initialized!"

if __name__ == "__main__":
    app.run(debug=True)
