from .models import ChatRoom, ChatMessage
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.contrib.auth.models import User
from .models import PrivateChatSession, PrivateMessage

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_slug = self.scope['url_route']['kwargs']['room_slug']
        self.room_group_name = f'chat_{self.room_slug}'
        if self.scope["user"].is_anonymous:
            await self.close()
        else:
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        user = self.scope["user"]
        await self.save_message(user, message)
        await self.channel_layer.group_send(self.room_group_name, {
            'type': 'chat_message',
            'message': message,
            'user': user.username,
            'timestamp': str(timezone.now()),
        })

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'user': event['user'],
            'message': event['message'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def save_message(self, user, content):
        room = ChatRoom.objects.get(slug=self.room_slug)
        msg = ChatMessage(room=room, user=user)
        msg.set_content(content)
        msg.save()


import logging
logger = logging.getLogger(__name__)

class PrivateChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        logger.info(f"PrivateChatConsumer connect attempt - user: {self.scope['user']}")
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            logger.warning("Anonymous user rejected")
            await self.close()
            return

        self.other_user_id = self.scope['url_route']['kwargs']['user_id']
        try:
            self.other_user = await database_sync_to_async(User.objects.get)(id=self.other_user_id)
        except User.DoesNotExist:
            logger.error(f"Other user {self.other_user_id} does not exist")
            await self.close()
            return

        user_ids = sorted([self.user.id, self.other_user.id])
        self.room_group_name = f"private_{user_ids[0]}_{user_ids[1]}"
        logger.info(f"Joining group: {self.room_group_name}")

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info("Connection accepted")

    async def disconnect(self, close_code):
        logger.info(f"Disconnected with code: {close_code}")
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        logger.info(f"Received message: {text_data}")
        try:
            data = json.loads(text_data)
            # 处理心跳消息
            if data.get('type') == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
                return

            # 处理普通消息
            message = data['message']
            await self.save_message(self.user, self.other_user, message)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'private_message',
                    'message': message,
                    'sender_id': self.user.id,
                    'sender_username': self.user.username,
                    'timestamp': str(timezone.now()),
                }
            )
        except KeyError as e:
            logger.error(f"Missing key in message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self.send(text_data=json.dumps({'error': 'Message processing failed'}))

    async def private_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'message': event['message'],
            'timestamp': event['timestamp'],
        }))

    @database_sync_to_async
    def save_message(self, sender, receiver, content):
        from .models import PrivateChatSession, PrivateMessage
        logger.info(f"Saving message from {sender.username} to {receiver.username}")
        session, _ = PrivateChatSession.objects.get_or_create(
            user1=sender if sender.id < receiver.id else receiver,
            user2=receiver if sender.id < receiver.id else sender,
        )
        msg = PrivateMessage(session=session, sender=sender, receiver=receiver)
        msg.set_content(content)
        msg.save()
        logger.info("Message saved")