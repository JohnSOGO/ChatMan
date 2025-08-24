# pip install tiktoklive flask
import time, threading
from threading import Lock
from flask import Flask, jsonify, send_from_directory
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent

# --- TikTokLive client (use your provided creator) ---
client: TikTokLiveClient = TikTokLiveClient(unique_id="@tostig.the.dm")

# Shared store of users -> last activity
users = {}  # uid -> { uid, name, last_comment, last_ts, count }
lock = Lock()

# --- Event handlers (compatible with your sample) ---
@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    print(f"Connected to @{event.unique_id} (Room ID: {client.room_id})")

async def on_comment(event: CommentEvent) -> None:
    # Be defensive about fields present in different lib versions
    uid = getattr(event.user, "uniqueId", None) or str(getattr(event.user, "userId", "unknown"))
    name = getattr(event.user, "nickname", uid)

    with lock:
        prev = users.get(uid, {})
        users[uid] = {
            "uid": uid,
            "name": name,
            "last_comment": event.comment,
            "last_ts": time.time(),
            "count": prev.get("count", 0) + 1
        }

client.add_listener(CommentEvent, on_comment)

# --- Flask app serving static HTML + JSON data ---
app = Flask(__name__, static_folder="static")

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/data.json")
def data_json():
    with lock:
        data = sorted(users.values(), key=lambda u: u["last_ts"], reverse=True)
    return jsonify(data)

def run_flask():
    # Local only; change host to "0.0.0.0" if you want LAN access
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Start the web UI
    threading.Thread(target=run_flask, daemon=True).start()
    # Start TikTok client (blocking, per your sample)
    client.run()
