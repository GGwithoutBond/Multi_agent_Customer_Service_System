import asyncio
import uuid
from src.core.events import lifespan
from src.database.session import get_db_session
from src.services.conversation_service import ConversationService
from src.services.chat_service import ChatService
from src.models.user import User
from fastapi import FastAPI

async def run_direct_test():
    app = FastAPI()
    async with lifespan(app):
        # We need a db session
        # get_db_session is an async generator
        gen = get_db_session()
        db = await anext(gen)
        try:
            user_id = uuid.uuid4()
            # Create a user first
            user = User(id=user_id, email=f"test_{user_id}@example.com", username=f"test_user_{user_id}", hashed_password="dummy")
            db.add(user)
            await db.commit()
            
            # Start a conversation
            conv_service = ConversationService(db)
            conv = await conv_service.create_conversation(user_id=user_id, channel="web")
            conv_id = str(conv.id)
            print(f"--- Created Conversation: {conv_id} ---")

            chat_service = ChatService(db)
            
            print("\n--- 1. Send Complaint (Create Ticket) ---")
            # We use stream to simulate the real chat
            async for chunk in chat_service.process_message_stream(
                message="我对你们的产品有点失望，想投诉并要求退款",
                conversation_id=uuid.UUID(conv_id),
                user_id=user_id,
                context={}
            ):
                if chunk.content:
                    print(chunk.content, end="", flush=True)

            print("\n\n--- 2. Query Ticket Status ---")
            async for chunk in chat_service.process_message_stream(
                message="帮我查查刚才给我创建的工单现在的进度怎么样了？",
                conversation_id=uuid.UUID(conv_id),
                user_id=user_id,
                context={}
            ):
                if chunk.content:
                    print(chunk.content, end="", flush=True)

            print("\n\n--- 3. Escalate Ticket ---")
            async for chunk in chat_service.process_message_stream(
                message="这也太慢了，马上叫人给我加急办理！！！",
                conversation_id=uuid.UUID(conv_id),
                user_id=user_id,
                context={}
            ):
                if chunk.content:
                    print(chunk.content, end="", flush=True)
                    
        finally:
            try:
                await anext(gen)
            except StopAsyncIteration:
                pass

if __name__ == "__main__":
    asyncio.run(run_direct_test())
