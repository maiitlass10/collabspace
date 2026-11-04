import json

from channels.generic.websocket import AsyncWebsocketConsumer


class PingConsumer(AsyncWebsocketConsumer):
    """
    Diagnostic consumer used in Phase 1 to prove that WebSockets work
    end-to-end (browser -> Vite proxy -> Daphne -> Channels).
    """

    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({"type": "welcome"}))

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error", "detail": "invalid_json"}))
            return

        if isinstance(payload, dict) and payload.get("type") == "ping":
            await self.send(text_data=json.dumps({"type": "pong", "id": payload.get("id")}))
        else:
            await self.send(text_data=json.dumps({"type": "error", "detail": "unknown_type"}))
