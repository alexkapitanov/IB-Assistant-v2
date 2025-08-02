import pytest
import asyncio

@pytest.mark.asyncio
async def test_status_pubsub():
    from backend import status_bus as sb
    tid = "test123"

    async def collector():
        async for d in sb.listen(tid):
            return d

    # Start collector
    task = asyncio.create_task(collector())
    # Publish status
    await sb.publish(tid, "thinking", None)
    # Await result
    res = await asyncio.wait_for(task, timeout=1)
    assert res["stage"] == "thinking"
    assert res.get("thread") == tid
    assert res.get("detail") is None
