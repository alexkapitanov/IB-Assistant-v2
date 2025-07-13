from fastapi import FastAPI, WebSocket, Depends
from backend.router import handle_message
from backend.chat_db import log_message
from backend.protocol import WsOutgoing
from backend.status_bus import publish, subscribe
import uuid
import asyncio

app = FastAPI()
sessions = {}

@app.get("/health")
def health(): return {"ok": True}

@app.websocket("/ws")
async def chat(ws: WebSocket):
    try:
        await ws.accept()
        thread_id = str(uuid.uuid4())
        sessions[ws] = thread_id
        asyncio.create_task(_status_forwarder(ws, thread_id))   # ← новый таск
        while True:
            data = await ws.receive_text()
            resp = await handle_message(thread_id, data)
            await ws.send_json(resp)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if ws in sessions:
            del sessions[ws]

async def _status_forwarder(ws: WebSocket, thread_id: str):
    try:
        async for st in subscribe(thread_id):
            await ws.send_json(WsOutgoing(type="status", status=st).dict())
    except Exception as e:
        print(f"❌ Status forwarder error: {e}")
        import traceback
        traceback.print_exc()
