from channels.testing import WebsocketCommunicator
from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from config.asgi import application


class HealthEndpointTests(TestCase):
    def test_health_returns_ok_without_authentication(self):
        response = self.client.get(reverse("health"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")
        self.assertEqual(response.json()["database"], "ok")


class PingConsumerTests(SimpleTestCase):
    async def _connect(self):
        communicator = WebsocketCommunicator(
            application, "/ws/ping/", headers=[(b"origin", b"http://localhost")]
        )
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        self.assertEqual(await communicator.receive_json_from(), {"type": "welcome"})
        return communicator

    async def test_ping_pong(self):
        communicator = await self._connect()
        await communicator.send_json_to({"type": "ping", "id": 7})
        self.assertEqual(await communicator.receive_json_from(), {"type": "pong", "id": 7})
        await communicator.disconnect()

    async def test_invalid_json_returns_error(self):
        communicator = await self._connect()
        await communicator.send_to(text_data="not json")
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "error")
        await communicator.disconnect()

    async def test_foreign_origin_is_rejected(self):
        communicator = WebsocketCommunicator(
            application, "/ws/ping/", headers=[(b"origin", b"http://evil.example.com")]
        )
        connected, _ = await communicator.connect()
        self.assertFalse(connected)
