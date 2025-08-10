#!/usr/bin/env python3
"""
Скрипт для синтетической генерации метрик Web-search Timeouts, Status Bus, Expert GC
"""
import asyncio
import json
import random
import time

import websockets


# --- Web-search Timeouts ---
async def generate_websearch_timeouts():
    print("⏳ Генерирую Web-search Timeouts...")
    uri = "ws://localhost:8000/ws"
    # Запросы, которые гарантированно вызовут таймаут (например, несуществующие сайты или слишком длинные запросы)
    timeout_queries = [
        "Поищи информацию на сайте, которого не существует: http://timeout-test-{}.com".format(random.randint(10000,99999)),
        "Найди 1000000 статей про неизвестную тему {}".format(random.randint(10000,99999)),
        "Проведи сложный websearch по несуществующему ресурсу {}".format(random.randint(10000,99999)),
    ]
    for query in timeout_queries:
        try:
            async with asyncio.timeout(15):
                async with websockets.connect(uri) as ws:
                    await ws.send(json.dumps({"message": query, "thread_id": f"timeout-{int(time.time())}"}))
                    print(f"📤 Websearch Timeout запрос: {query[:60]}...")
                    # Ждем ответ или таймаут
                    response_count = 0
                    async for msg in ws:
                        response_count += 1
                        if response_count > 2:
                            break
        except Exception as e:
            print(f"⏰ Ожидаемый таймаут: {e}")
        await asyncio.sleep(2)

# --- Expert GC ---
async def generate_expert_gc():
    print("🧠 Генерирую Expert GC...")
    uri = "ws://localhost:8000/ws"
    expert_queries = [
        "Проанализируй 10 подходов к оптимизации нейронных сетей и сравни их эффективность",
        "Сделай глубокий анализ современных методов машинного обучения для медицины",
        "Проведи экспертную оценку алгоритмов квантового машинного обучения"
    ]
    for query in expert_queries:
        try:
            async with asyncio.timeout(15):
                async with websockets.connect(uri) as ws:
                    await ws.send(json.dumps({"message": query, "thread_id": f"expert-{int(time.time())}"}))
                    print(f"📤 Expert GC запрос: {query[:60]}...")
                    response_count = 0
                    async for msg in ws:
                        response_count += 1
                        if response_count > 3:
                            break
        except Exception as e:
            print(f"⏰ Expert GC таймаут: {e}")
        await asyncio.sleep(2)

# --- Status Bus ---
async def generate_status_bus():
    print("📡 Генерирую Status Bus...")
    uri = "ws://localhost:8000/ws"
    tasks = []
    for i in range(5):
        async def status_task(idx):
            try:
                async with asyncio.timeout(10):
                    async with websockets.connect(uri) as ws:
                        await ws.send(json.dumps({"message": f"Параллельный статус-запрос #{idx}", "thread_id": f"status-{idx}-{int(time.time())}"}))
                        print(f"📤 Status Bus запрос #{idx}")
                        response_count = 0
                        async for msg in ws:
                            response_count += 1
                            if response_count > 2:
                                break
            except Exception as e:
                print(f"⏰ Status Bus таймаут: {e}")
        tasks.append(status_task(i))
    await asyncio.gather(*tasks)

async def main():
    await generate_websearch_timeouts()
    await generate_expert_gc()
    await generate_status_bus()
    print("\n🎉 Синтетические метрики сгенерированы!")

if __name__ == "__main__":
    asyncio.run(main())
