import json
import base64
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.contrib.auth.models import User
from .models import PrivateChatSession, PrivateMessage, ChatRoom, ChatMessage

logger = logging.getLogger(__name__)

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
            msg_type = data.get('type')

            # 处理心跳
            if msg_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))
                return

            if msg_type == 'message':
                # 提取所有字段
                content = data.get('message', '').strip()
                encryption_type = data.get('encryption_type', 'system')
                is_burn = data.get('is_burn_after_reading', False)
                burn_at_str = data.get('burn_at', None)

                burn_at = parse_datetime(burn_at_str) if burn_at_str else None

                # 保存消息到数据库
                message_obj = await self.save_message(
                    sender=self.user,
                    receiver=self.other_user,
                    content=content,
                    encryption_type=encryption_type,
                    is_burn_after_reading=is_burn,
                    burn_at=burn_at
                )

                if message_obj:
                    # 广播消息给组内成员
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'private_message',
                            'message': {
                                'id': message_obj.id,
                                'sender_id': self.user.id,
                                'sender_username': self.user.username,
                                'message': content,  # 注意：对系统加密是明文，对自定义是base64密文
                                'encryption_type': encryption_type,
                                'is_burn_after_reading': is_burn,
                                'burn_at': burn_at.isoformat() if burn_at else None,
                                'created_at': message_obj.created_at.isoformat(),
                            }
                        }
                    )
                else:
                    await self.send(text_data=json.dumps({'type': 'error', 'message': '消息保存失败'}))

        except KeyError as e:
            logger.error(f"Missing key in message: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}", exc_info=True)
            await self.send(text_data=json.dumps({'error': 'Message processing failed'}))

    async def private_message(self, event):
        # 将广播的消息转发给 WebSocket 客户端
        await self.send(text_data=json.dumps({
            'type': 'message',
            **event['message']
        }))

    @database_sync_to_async
    def save_message(self, sender, receiver, content, encryption_type, is_burn_after_reading, burn_at):
        from .models import PrivateChatSession, PrivateMessage
        logger.info(
            f"save_message: sender={sender.id}, receiver={receiver.id}, type={encryption_type}, content_length={len(content)}")

        try:
            user1, user2 = sorted([sender, receiver], key=lambda u: u.id)
            session, _ = PrivateChatSession.objects.get_or_create(user1=user1, user2=user2)
            logger.debug(f"Session obtained: {session.id}")
        except Exception as e:
            logger.exception("Failed to get/create session")
            return None

        msg = PrivateMessage(
            session=session,
            sender=sender,
            receiver=receiver,
            encryption_type=encryption_type,
            is_burn_after_reading=is_burn_after_reading,
            burn_at=burn_at,
        )

        try:
            if encryption_type == 'system':
                logger.debug("Calling set_system_content...")
                msg.set_system_content(content)
                logger.debug(
                    f"set_system_content succeeded, encrypted_content length: {len(msg.encrypted_content) if msg.encrypted_content else 0}")
            else:
                logger.error(f"Unexpected encryption_type: {encryption_type}")
                return None

            logger.debug("Saving message...")
            msg.save()
            logger.info(f"Message saved, id={msg.id}")
            return msg
        except Exception as e:
            logger.exception(f"Exception in save_message: {e}")
            return None