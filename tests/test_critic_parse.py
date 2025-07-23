from agents.critic import _score_to_float

def test_score_parse_variants():
    assert _score_to_float("0.83 / 1") == 0.83
    assert _score_to_float("score:0.7") == 0.7
    assert _score_to_float("N/A") is None
