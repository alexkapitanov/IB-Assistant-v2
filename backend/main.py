from fastapi import FastAPI, WebSocket, Depends
from backend.router import handle_message
from backend.chat_db import log_message
import uuid

app = FastAPI()
sessions = {}

@app.get("/health")
def health(): return {"ok": True}

@app.websocket("/ws")
async def chat(ws: WebSocket):
    await ws.accept()
    thread_id = str(uuid.uuid4())
    sessions[ws] = thread_id
    while True:
        data = await ws.receive_text()
        resp = await handle_message(thread_id, data)
        await ws.send_json(resp)
