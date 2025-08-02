import uuid, logging, traceback

def capture(exc: Exception) -> str:
    eid = uuid.uuid4().hex[:12]
    logging.error("ERR %s\n%s", eid, traceback.format_exc())
    return eid
