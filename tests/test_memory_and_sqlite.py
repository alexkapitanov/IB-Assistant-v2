def test_memory_and_sqlite():
    import sys, os
    # Ensure backend module can be found
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))
    from memory import save_mem, get_mem
    from chat_db import log_message, _conn
    
    # Test memory save and retrieve
    tid = "t123"
    save_mem(tid, {"product": "Infowatch"})
    assert get_mem(tid)["product"] == "Infowatch"

    # Clean existing data for this thread
    with _conn() as c:
        c.execute("DELETE FROM chatlog WHERE thread_id=?", (tid,))

    # Test SQLite logging
    log_message(tid, 0, "user", "hi")
    with _conn() as c:
        cnt = c.execute(
            "select count(*) from chatlog where thread_id=?", (tid,)
        ).fetchone()[0]
    assert cnt == 1
