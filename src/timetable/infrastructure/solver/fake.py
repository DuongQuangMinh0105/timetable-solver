import json


def fake_handler(data: bytes) -> bytes:
    """Solver giả: không giải gì cả, chỉ trả về JSON cố định để kiểm tra luồng end-to-end."""
    return json.dumps({"status": "fake", "input_bytes": len(data)}).encode("utf-8")
