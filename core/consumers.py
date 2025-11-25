import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Message, User

def room_name(a, b):
    return "_".join(sorted([a, b]))

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if user.is_anonymous:
            await self.close()
            return
        other = self.scope["url_route"]["kwargs"]["username"]
        self.room_group_name = f"chat_{room_name(user.username, other)}"
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data.get("message")
        to_user = data.get("to")
        await database_sync_to_async(self.save_message)(self.scope["user"].username, to_user, message)
        await self.channel_layer.group_send(self.room_group_name, {
            "type": "chat_message",
            "message": message,
            "sender": self.scope["user"].username,
        })

    def save_message(self, sender, receiver, content):
        sender_user = User.objects.get(username=sender)
        receiver_user = User.objects.get(username=receiver)
        Message.objects.create(sender=sender_user, receiver=receiver_user, content=content)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            "message": event["message"],
            "sender": event["sender"],
        }))
