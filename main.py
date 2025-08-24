
from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent
import chat_store as store

print("DB file:", store.init_db())

tdm = "@tostig.the.dm"

client = TikTokLiveClient(unique_id=tdm)

@client.on(ConnectEvent)
async def on_connect(_):
    print(f"Connected. Logging to {store.DB_PATH.resolve()}")

async def on_comment(event: CommentEvent):
    msg_id = store.add_message(event.user.nickname, event.comment)
    print(f"[{msg_id}] {event.user.nickname} -> {event.comment}")

client.add_listener(CommentEvent, on_comment)

if __name__ == "__main__":
    client.run()
