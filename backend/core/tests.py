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


class ApiDocsTests(TestCase):
    """Sprint 7: the OpenAPI schema is complete and the docs page is public."""

    def test_schema_is_valid_without_warnings(self):
        from io import StringIO

        from django.core.management import call_command

        # --fail-on-warn: a new endpoint without proper docs breaks this test.
        call_command("spectacular", "--validate", "--fail-on-warn", stdout=StringIO(), stderr=StringIO())

    def test_docs_pages_are_public(self):
        schema = self.client.get("/api/schema/")
        self.assertEqual(schema.status_code, 200)
        self.assertIn(b"/api/documents/{document_pk}/versions/", schema.content)
        self.assertEqual(self.client.get("/api/docs/").status_code, 200)


class RedisChannelLayerConfigTests(SimpleTestCase):
    """Regression (found with Docker in Sprint 7): Redis reads must not time out
    while channels-redis is still waiting for messages."""

    def test_socket_timeout_is_longer_than_the_blocking_wait(self):
        from channels_redis.core import RedisChannelLayer
        from channels_redis.utils import create_pool

        from config.channel_layers import channel_layers

        config = channel_layers("redis://localhost:6379/0")["default"]
        layer = RedisChannelLayer(**config["CONFIG"])
        pool = create_pool(layer.hosts[0])  # what channels-redis builds (no connection is opened)
        self.assertGreater(pool.connection_kwargs["socket_timeout"], RedisChannelLayer.brpop_timeout * 2)

    def test_in_memory_without_redis_url(self):
        from config.channel_layers import channel_layers

        self.assertEqual(channel_layers("")["default"]["BACKEND"], "channels.layers.InMemoryChannelLayer")
