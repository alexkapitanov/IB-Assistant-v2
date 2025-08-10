import asyncio

import websockets


async def main():
    uri = "ws://localhost:8000/ws"
    for _ in range(20):
        try:
            async with websockets.connect(uri) as ws:
                print("ws ok")
                return
        except Exception:
            await asyncio.sleep(0.5)
    raise SystemExit("ws not ready")


if __name__ == "__main__":
    asyncio.run(main())
