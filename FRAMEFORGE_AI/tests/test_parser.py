from ai.response_parser import ParseError, extract_json


def test_fenced_trailing_comma_and_think():
    assert extract_json('<think>x</think>```json\n{"a":[1,2,],"b":"x"}\n```') == {"a": [1, 2], "b": "x"}


def test_truncated_json_is_repaired():
    d = extract_json('{"scenes":[{"block_id":"B001","description":"A man walks')
    assert d["scenes"][0]["block_id"] == "B001"


def test_prose_around_json():
    assert extract_json('Sure! {"a": 1} Hope that helps.') == {"a": 1}


def test_garbage_raises():
    try:
        extract_json("no json here")
    except ParseError:
        return
    raise AssertionError("expected ParseError")
