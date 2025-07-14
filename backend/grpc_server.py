import asyncio, uuid, json
from grpclib.server import Server
from backend.chat_core import chat_stream
from backend import chat_pb2, chat_grpc

class Chat(chat_grpc.ChatBase):

    async def Stream(self, stream):
        thread = str(uuid.uuid4())
        q_in, q_out = asyncio.Queue(), asyncio.Queue()
        # Запускаем движок
        task = asyncio.create_task(chat_stream(thread, q_in, q_out))
        
        async def sender():
            while True:
                msg = await q_out.get()
                if msg is None:  # Сигнал завершения
                    break
                # Преобразуем внутренний формат в protobuf ChatMessage
                pb_msg = chat_pb2.ChatMessage(
                    role=msg.get("role", ""),
                    content=msg.get("content", ""),
                    status=msg.get("status", "")
                )
                await stream.send_message(pb_msg)
                
        send_task = asyncio.create_task(sender())
        
        # Читаем входящий поток
        async for req in stream:
            if req.content:
                # Формируем JSON-строку для совместимости с chat_stream
                message_json = json.dumps({"message": req.content})
                await q_in.put(message_json)
                
        await q_in.put(None)          # graceful stop
        await task
        await q_out.put(None)         # сигнал завершения для sender
        await send_task               # ждем завершения отправки

async def serve():
    server = Server([Chat()])
    await server.start("0.0.0.0", 50051)
    await server.wait_closed()

if __name__ == '__main__':
    asyncio.run(serve())
