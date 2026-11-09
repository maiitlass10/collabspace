"""Channel layer configuration (see CHANNEL_LAYERS in settings.py)."""

# channels-redis waits up to 5 s on Redis for the next message (BZPOPMIN),
# and redis-py 8 ALSO times out socket reads after 5 s by default. When both
# hit at the same moment the read fails, the WebSocket consumer crashes, and
# its cleanup never runs (ghost presence, a room that is never released).
# So the socket timeout must be clearly longer than the blocking wait.
REDIS_SOCKET_TIMEOUT_SECONDS = 30


def channel_layers(redis_url: str) -> dict:
    if not redis_url:
        return {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
    return {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [{"address": redis_url, "socket_timeout": REDIS_SOCKET_TIMEOUT_SECONDS}],
            },
        }
    }
