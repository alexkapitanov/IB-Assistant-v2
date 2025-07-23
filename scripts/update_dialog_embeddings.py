import sqlite3
import qdrant_client
from qdrant_client.models import Distance, VectorParams, PointStruct
import json
import tqdm
from backend.embedding_pool import get_embedding_async
import asyncio

def main():
    """
    Основная функция для обновления эмбеддингов диалогов.
    Извлекает диалоги из SQLite, генерирует эмбеддинги для вопросов
    и загружает их вместе с ответами в Qdrant.
    """
    # Подключение к базе данных
    # Путь к базе данных должен совпадать с тем, что используется в chat_db.py
    conn = sqlite3.connect("/data/chatlog.db")
    
    # Подключение к Qdrant
    qdr = qdrant_client.QdrantClient("qdrant", port=6333)

        # Проверка и создание коллекции 'dialogs', если она не существует
    try:
        qdr.get_collection(collection_name="dialogs")
        print("Коллекция 'dialogs' уже существует.")
    except:
        print("Создание коллекции 'dialogs'...")
        qdr.create_collection(
            collection_name="dialogs",
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
        print("Коллекция 'dialogs' создана.")

    cur = conn.execute("SELECT thread_id, body, ts FROM dialog_log ORDER BY ts")
    
    print("Starting to process dialogs...")
    
    for row in tqdm.tqdm(list(cur)):
        tid, body, ts = row
        
        try:
            msgs = json.loads(body)
            if len(msgs) < 2:  # Нужен как минимум вопрос и ответ
                continue

            # Предполагаем, что первое сообщение - вопрос, последнее - ответ
            question = msgs[0]["content"]
            answer = msgs[-1]["content"]
            
            # Проверяем, что роли соответствуют вопросу и ответу
            if msgs[0]["role"] not in ["user", "human"] or msgs[-1]["role"] not in ["assistant", "ai"]:
                continue

            # Получаем эмбеддинг для вопроса
            emb = asyncio.run(get_embedding_async(question))

            # Загружаем в Qdrant
            qdr.upsert(
                collection_name="dialogs",
                wait=True,
                points=[
                    PointStruct(
                        id=tid, 
                        vector=emb,
                        payload={"answer": answer, "question": question, "ts": ts}
                    )
                ]
            )
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Could not process thread {tid}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred with thread {tid}: {e}")

    print("Finished processing dialogs.")
    conn.close()

if __name__ == "__main__":
    main()
