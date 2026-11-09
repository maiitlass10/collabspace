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


def parse_awareness_update(update: bytes) -> list[tuple[int, int, str]]:
    """
    Parse an awareness update payload:
        count, then for each client: client_id, clock, state (JSON string)
    Returns [(client_id, clock, state_json)].
    """
    decoder = Decoder(update)
    count = decoder.read_var_uint()
    result = []
    for _ in range(count):
        client_id = decoder.read_var_uint()
        clock = decoder.read_var_uint()
        state = decoder.read_var_string()
        result.append((client_id, clock, state))
    return result


def write_var_uint(value: int) -> bytes:
    """Encode a lib0 var-uint."""
    out = bytearray()
    while value > 0x7F:
        out.append(0x80 | (value & 0x7F))
        value >>= 7
    out.append(value)
    return bytes(out)


def write_var_string(text: str) -> bytes:
    """
    Encode a lib0 string: byte length, then UTF-8 bytes.
    (pycrdt's Encoder.write_var_string writes the CHARACTER count, which
    breaks any non-ASCII text such as Arabic names, so we do it ourselves.)
    """
    data = text.encode("utf-8")
    return write_var_uint(len(data)) + data


def encode_awareness_update(entries: list[tuple[int, int, str]]) -> bytes:
    """The reverse of parse_awareness_update."""
    out = bytearray(write_var_uint(len(entries)))
    for client_id, clock, state in entries:
        out += write_var_uint(client_id)
        out += write_var_uint(clock)
        out += write_var_string(state)
    return bytes(out)


def awareness_client_states(update: bytes) -> list[tuple[int, bool]]:
    """
    Returns [(client_id, is_alive)], where is_alive is False for "null" states
    (a client announcing it is leaving).
    """
    return [(client_id, state != "null") for client_id, _clock, state in parse_awareness_update(update)]
