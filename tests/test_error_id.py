from backend.utils.error_id import capture

def test_error_id():
    eid = capture(Exception("x"))
    assert len(eid) == 12
