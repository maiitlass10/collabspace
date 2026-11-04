"""
Helpers for the Yjs WebSocket protocol (the one spoken by the `y-websocket`
JavaScript client).

Every binary message starts with a message type (var-uint):
    0 = SYNC        -> followed by a sync sub-type:
                        0 = STEP1  (state vector: "this is what I have")
                        1 = STEP2  (update: "here is what you are missing")
                        2 = UPDATE (a live edit)
    1 = AWARENESS   -> presence info (name, color, cursor position)
    3 = QUERY_AWARENESS
"""
from pycrdt import Decoder, YMessageType, YSyncMessageType  # noqa: F401  (re-exported)

MSG_SYNC = 0
MSG_AWARENESS = 1
MSG_AUTH = 2
MSG_QUERY_AWARENESS = 3

SYNC_STEP1 = 0
SYNC_STEP2 = 1
SYNC_UPDATE = 2

# An empty Yjs update (no structs, empty delete set).
EMPTY_UPDATE = b"\x00\x00"


def read_var_uint(data: bytes, pos: int = 0) -> tuple[int, int]:
    """Decode a lib0 var-uint. Returns (value, new_position)."""
    value = 0
    shift = 0
    while True:
        byte = data[pos]
        pos += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, pos
        shift += 7


def read_var_bytes(data: bytes, pos: int = 0) -> tuple[bytes, int]:
    """Decode a length-prefixed byte array. Returns (bytes, new_position)."""
    length, pos = read_var_uint(data, pos)
    end = pos + length
    if end > len(data):
        raise ValueError("Truncated message")
    return data[pos:end], end


def awareness_client_states(update: bytes) -> list[tuple[int, bool]]:
    """
    Parse an awareness update payload.
    Returns [(client_id, is_alive)], where is_alive is False for "null" states
    (a client announcing it is leaving).
    """
    decoder = Decoder(update)
    count = decoder.read_var_uint()
    result = []
    for _ in range(count):
        client_id = decoder.read_var_uint()
        decoder.read_var_uint()  # clock
        state = decoder.read_var_string()
        result.append((client_id, state != "null"))
    return result
