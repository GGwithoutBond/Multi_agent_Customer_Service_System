import asyncio
import httpx
import json

async def test_complaint():
    async with httpx.AsyncClient(base_url='http://127.0.0.1:8001', proxy=None) as client:
        # 1. Start a conversation
        print("--- Starting conversation ---")
        resp = await client.post('/api/v1/conversations', json={'user_id': '00000000-0000-0000-0000-000000000000'})
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
        conv_id = resp.json()['data']['id']
        print(f'Conversation ID: {conv_id}')
        
        # 2. Send a complaint message
        print("\n--- Sending complaint ---")
        async with client.stream("POST", f'/api/v1/chat/stream', json={
            'conversation_id': conv_id,
            'message': '我对你们的产品质量非常不满意，我要投诉！要求退款！这事非常急！',
            'user_id': '00000000-0000-0000-0000-000000000000'
        }, timeout=30.0) as response:
            async for chunk in response.aiter_text():
                print(chunk, end='', flush=True)
                
        # 3. Ask for the ticket progress
        print("\n\n--- Asking for progress ---")
        async with client.stream("POST", f'/api/v1/chat/stream', json={
            'conversation_id': conv_id,
            'message': '帮我查查刚才工单的进度',
            'user_id': '00000000-0000-0000-0000-000000000000'
        }, timeout=30.0) as response:
            async for chunk in response.aiter_text():
                print(chunk, end='', flush=True)

        # 4. Ask to escalate the ticket
        print("\n\n--- Escalate ticket ---")
        async with client.stream("POST", f'/api/v1/chat/stream', json={
            'conversation_id': conv_id,
            'message': '你们处理太慢了，帮我加急催办一下！！！',
            'user_id': '00000000-0000-0000-0000-000000000000'
        }, timeout=30.0) as response:
            async for chunk in response.aiter_text():
                print(chunk, end='', flush=True)
                
if __name__ == '__main__':
    asyncio.run(test_complaint())
