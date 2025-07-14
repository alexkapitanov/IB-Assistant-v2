from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.websockets import WebSocketDisconnect
from backend.router import handle_message
from backend.auth import check_auth_header
from backend.chat_db import log_message
from backend.protocol import WsOutgoing
from backend.status_bus import publish, subscribe
from backend.upload import upload_file
from backend.json_utils import NpEncoder
from backend.openai_helpers import setup_qdrant
from backend.ratelimit import check_rate_limit
from backend.env_validator import validate_environment
from prometheus_fastapi_instrumentator import Instrumentator
from backend import grpc_server
from backend.chat_core import chat_stream
import json
import uuid
import asyncio
import logging
import traceback
import os
from datetime import datetime
from typing import Dict, Any

# Настройка логгера
logger = logging.getLogger(__name__)

app = FastAPI(
    title="IB Assistant v2 API",
    description="Investment Banking Assistant with AI-powered research capabilities",
    version="2.0.0",
    lifespan=lifespan
)

async def lifespan(app: FastAPI):
    # Действия при старте
    logger.info("Application startup")
    await setup_qdrant(recreate_collection=True) # Создаем коллекцию при старте
    yield
    # Действия при завершении
    logger.info("Application shutdown")

# Prometheus metrics
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

# CORS middleware for GitHub Codespaces / GH Pages
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

sessions = {}

async def _safe_send(ws, role, content):
    """Безопасная отправка сообщения через WebSocket"""
    await ws.send_json(WsOutgoing(type="chat", role=role, content=content).dict())

@app.get("/health")
def health(): 
    return {"ok": True, "timestamp": datetime.utcnow().isoformat()}

@app.get("/version")
def version():
    """Get system version and build information"""
    return {
        "version": "2.0.0",
        "build_time": datetime.utcnow().isoformat(),
        "environment": os.getenv("ENVIRONMENT", "development"),
        "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}",
        "features": [
            "websocket_chat",
            "vector_search", 
            "markdown_rendering",
            "rate_limiting",
            "token_accounting",
            "prometheus_metrics",
            "dark_theme"
        ]
    }

@app.get("/validate")
async def validate():
    """Validate environment configuration and external dependencies"""
    try:
        result = await validate_environment()
        return result
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        return {
            "overall_status": "fail",
            "summary": {"total_checks": 1, "passed": 0, "warnings": 0, "failed": 1},
            "checks": [{
                "name": "Validation execution",
                "status": "fail", 
                "message": "Failed to run validation",
                "details": str(e)
            }]
        }

@app.websocket("/ws")
async def chat(ws: WebSocket):
    status_task = None
    stream_task = None
    q_in, q_out = asyncio.Queue(), asyncio.Queue()
    try:
        await ws.accept()
        print("✅ WebSocket connection accepted")
        thread_id = str(uuid.uuid4())
        sessions[ws] = thread_id
        
        status_task = asyncio.create_task(_status_forwarder(ws, thread_id))
        stream_task = asyncio.create_task(chat_stream(thread_id, q_in, q_out))
        
        print(f"📡 Status forwarder and chat stream started for thread {thread_id}")
        
        # Получаем IP клиента для rate limiting
        client_ip = ws.client.host if ws.client else "unknown"
        
        # Запускаем sender для отправки сообщений из очереди в WebSocket
        async def sender():
            while True:
                resp = await q_out.get()
                if resp is None: # Сигнал для завершения
                    break
                print(f"📤 Sending response: {resp}")
                await ws.send_json(resp)
                print("✅ Response sent successfully")

        sender_task = asyncio.create_task(sender())

        while True:
            print("⏳ Waiting for message...")
            data = await ws.receive_text()
            print(f"📨 Received: {data}")
            
            # Проверяем rate limit
            if await check_rate_limit(client_ip):
                logger.warning(f"Rate limit exceeded for IP: {client_ip}")
                await ws.close(code=4008, reason="Rate limit exceeded")
                break
            
            await q_in.put(data)
            
    except WebSocketDisconnect as e:
        print(f"🔌 WebSocket disconnected normally: {e}")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        traceback.print_exc()
    finally:
        print("🧹 Cleaning up WebSocket connection...")
        if status_task and not status_task.done():
            print("🛑 Cancelling status forwarder task")
            status_task.cancel()
        
        # Корректное завершение
        if q_in:
            await q_in.put(None) # Сигнал для chat_stream
        if stream_task and not stream_task.done():
            await stream_task
        if q_out:
            await q_out.put(None) # Сигнал для sender_task

        if ws in sessions:
            print(f"🗑️ Removing session for thread {sessions[ws]}")
            del sessions[ws]
        print("✅ WebSocket cleanup complete")

async def _status_forwarder(ws: WebSocket, thread_id: str):
    try:
        async for st in subscribe(thread_id):
            await ws.send_json(WsOutgoing(type="status", status=st).dict())
    except Exception as e:
        print(f"❌ Status forwarder error: {e}")
        import traceback
        traceback.print_exc()
