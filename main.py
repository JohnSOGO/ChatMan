from TikTokLive import TikTokLiveClient
from TikTokLive.events import ConnectEvent, CommentEvent
import json

user_list = []

def update_user_list(nickname):
    global user_list
    if nickname in user_list:
        user_list.remove(nickname)
    user_list.insert(0, nickname)
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(user_list, f, ensure_ascii=False, indent=2)

# Create the client
client: TikTokLiveClient = TikTokLiveClient(unique_id="@naqss_")


# Listen to an event with a decorator!
@client.on(ConnectEvent)
async def on_connect(event: ConnectEvent):
    print(f"Connected to @{event.unique_id} (Room ID: {client.room_id}")
    update_user_list(event.unique_id)


# Or, add it manually via "client.add_listener()"
async def on_comment(event: CommentEvent) -> None:
    print(f"{event.user.nickname} -> {event.comment}")


client.add_listener(CommentEvent, on_comment)

if __name__ == '__main__':
    # Run the client and block the main thread
    # await client.start() to run non-blocking
    client.run()