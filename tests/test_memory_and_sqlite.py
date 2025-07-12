def test_memory_and_sqlite():
    from backend.memory import save_mem, get_mem
    from backend.chat_db import log_message, _conn
    # Test memory save and retrieve
    tid = "t123"
    save_mem(tid, {"product": "Infowatch"})
    assert get_mem(tid)["product"] == "Infowatch"

    # Test SQLite logging
    log_message(tid, 0, "user", "hi")
    with _conn() as c:
        cnt = c.execute(
            "select count(*) from chatlog where thread_id=?", (tid,)
        ).fetchone()[0]
    assert cnt == 1
