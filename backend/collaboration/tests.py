import asyncio

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.test import Client, TransactionTestCase
from pycrdt import Doc, Text, create_sync_message, create_update_message

from config.asgi import application
from documents.models import Document

from . import protocol, rooms as rooms_module
from .rooms import rooms

User = get_user_model()


def session_headers(user):
    client = Client()
    client.force_login(user)
    cookie = f"sessionid={client.cookies['sessionid'].value}"
    return [(b"cookie", cookie.encode()), (b"origin", b"http://localhost")]


def text_of(state: bytes) -> str:
    doc = Doc()
    if state:
        doc.apply_update(state)
    doc["content"] = text = Text()
    return str(text)


class YClient:
    """A minimal Yjs client built on pycrdt, talking to our consumer."""

    def __init__(self, user, document_id):
        self.user = user
        self.document_id = document_id
        self.doc = Doc()
        self.doc["content"] = self.text = Text()
        self.ws = None
        self.pending = []  # non-sync messages received during the handshake

    async def connect(self):
        headers = await database_sync_to_async(session_headers)(self.user)
        self.ws = WebsocketCommunicator(application, f"/ws/documents/{self.document_id}/", headers=headers)
        connected, _ = await self.ws.connect()
        assert connected
        # Server sends SYNC_STEP1 first; answer it, then send our own STEP1.
        first = await self.ws.receive_from()
        assert first[0] == protocol.MSG_SYNC and first[1] == protocol.SYNC_STEP1
        await self.ws.send_to(bytes_data=create_sync_message(self.doc))
        while True:
            reply = await self.ws.receive_from()
            if reply[0] == protocol.MSG_SYNC and reply[1] == protocol.SYNC_STEP2:
                self.apply(reply)
                return
            self.pending.append(reply)

    def apply(self, message: bytes):
        if message[0] == protocol.MSG_SYNC and message[1] in (protocol.SYNC_STEP2, protocol.SYNC_UPDATE):
            update, _ = protocol.read_var_bytes(message, 2)
            if update != protocol.EMPTY_UPDATE:
                self.doc.apply_update(update)

    async def insert(self, index, value):
        before = self.doc.get_state()
        self.text.insert(index, value)
        update = self.doc.get_update(before)
        await self.ws.send_to(bytes_data=create_update_message(update))

    async def receive_update(self):
        message = await self.ws.receive_from(timeout=2)
        self.apply(message)
        return message


class DocumentConsumerTests(TransactionTestCase):
    def setUp(self):
        rooms._rooms.clear()
        rooms_module.SAVE_DELAY_SECONDS = 0.05
        self.owner = User.objects.create_user(email="o@example.com", password="x", display_name="Owner")
        self.stranger = User.objects.create_user(email="s@example.com", password="x", display_name="Stranger")
        self.document = Document.objects.create(owner=self.owner, title="Doc")

    def tearDown(self):
        rooms_module.SAVE_DELAY_SECONDS = 2.0

    async def close_code(self, headers):
        ws = WebsocketCommunicator(application, f"/ws/documents/{self.document.id}/", headers=headers)
        connected, _ = await ws.connect()
        self.assertTrue(connected)  # accepted, then closed with an explanatory code
        output = await ws.receive_output(timeout=2)
        self.assertEqual(output["type"], "websocket.close")
        return output["code"]

    async def test_anonymous_user_is_rejected(self):
        code = await self.close_code([(b"origin", b"http://localhost")])
        self.assertEqual(code, 4401)

    async def test_user_without_access_is_rejected(self):
        headers = await database_sync_to_async(session_headers)(self.stranger)
        self.assertEqual(await self.close_code(headers), 4403)

    async def test_unknown_document_is_rejected(self):
        headers = await database_sync_to_async(session_headers)(self.owner)
        ws = WebsocketCommunicator(application, "/ws/documents/00000000-0000-0000-0000-000000000000/", headers=headers)
        await ws.connect()
        self.assertEqual((await ws.receive_output(timeout=2))["code"], 4403)

    async def test_edit_is_broadcast_to_other_client(self):
        a = YClient(self.owner, self.document.id)
        b = YClient(self.owner, self.document.id)
        await a.connect()
        await b.connect()

        await a.insert(0, "مرحبا")
        await b.receive_update()
        self.assertEqual(str(b.text), "مرحبا")

        # The sender does not get its own edit echoed back.
        self.assertTrue(await a.ws.receive_nothing(timeout=0.2))
        await a.ws.disconnect()
        await b.ws.disconnect()

    async def test_concurrent_edits_converge(self):
        a = YClient(self.owner, self.document.id)
        b = YClient(self.owner, self.document.id)
        await a.connect()
        await b.connect()
        await a.insert(0, "AAA")
        await b.insert(0, "BBB")
        await a.receive_update()
        await b.receive_update()
        self.assertEqual(str(a.text), str(b.text))
        self.assertIn("AAA", str(a.text))
        self.assertIn("BBB", str(a.text))
        await a.ws.disconnect()
        await b.ws.disconnect()

    async def test_content_is_saved_and_restored(self):
        a = YClient(self.owner, self.document.id)
        await a.connect()
        await a.insert(0, "saved text")
        await asyncio.sleep(0.2)  # debounce save
        await a.ws.disconnect()

        await database_sync_to_async(self.document.refresh_from_db)()
        self.assertEqual(text_of(bytes(self.document.yjs_state)), "saved text")
        self.assertEqual(len(rooms), 0, "room is released when the last user leaves")

        # A new client gets the saved content during the initial sync.
        c = YClient(self.owner, self.document.id)
        await c.connect()
        self.assertEqual(str(c.text), "saved text")
        await c.ws.disconnect()

    async def test_last_user_leaving_saves_immediately(self):
        rooms_module.SAVE_DELAY_SECONDS = 60  # the timer would never fire during the test
        a = YClient(self.owner, self.document.id)
        await a.connect()
        await a.insert(0, "flush on leave")
        await asyncio.sleep(0.05)
        await a.ws.disconnect()
        await database_sync_to_async(self.document.refresh_from_db)()
        self.assertEqual(text_of(bytes(self.document.yjs_state)), "flush on leave")

    async def test_garbage_message_does_not_crash_the_room(self):
        a = YClient(self.owner, self.document.id)
        await a.connect()
        with self.assertLogs("collaboration.consumers", level="WARNING") as logs:
            await a.ws.send_to(bytes_data=b"\x00\x02\xff\xff\xff")
            await asyncio.sleep(0.05)
        self.assertIn("Invalid Yjs message", logs.output[0])
        await a.ws.send_to(bytes_data=b"\x63")  # unknown type: silently ignored
        await a.insert(0, "still works")
        await asyncio.sleep(0.1)
        room = rooms.get(str(self.document.id))
        self.assertIsNotNone(room)
        await a.ws.disconnect()
        await database_sync_to_async(self.document.refresh_from_db)()
        self.assertEqual(text_of(bytes(self.document.yjs_state)), "still works")


class AwarenessTests(TransactionTestCase):
    def setUp(self):
        rooms._rooms.clear()
        self.owner = User.objects.create_user(email="o@example.com", password="x", display_name="Owner")
        self.document = Document.objects.create(owner=self.owner, title="Doc")

    @staticmethod
    def awareness_message(client_id, clock, state_json):
        from pycrdt import Encoder, create_awareness_message

        encoder = Encoder()
        encoder.write_var_uint(1)
        encoder.write_var_uint(client_id)
        encoder.write_var_uint(clock)
        encoder.write_var_string(state_json)
        return create_awareness_message(encoder.to_bytes())

    async def test_presence_is_relayed_and_cleared_on_disconnect(self):
        a = YClient(self.owner, self.document.id)
        b = YClient(self.owner, self.document.id)
        await a.connect()
        await b.connect()

        await a.ws.send_to(bytes_data=self.awareness_message(111, 1, '{"user":{"name":"A"}}'))
        relayed = await b.ws.receive_from(timeout=2)
        self.assertEqual(relayed[0], protocol.MSG_AWARENESS)
        payload, _ = protocol.read_var_bytes(relayed, 1)
        self.assertEqual(protocol.awareness_client_states(payload), [(111, True)])

        # A newcomer is told who is already in the document.
        c = YClient(self.owner, self.document.id)
        await c.connect()
        welcome = c.pending[0]
        self.assertEqual(welcome[0], protocol.MSG_AWARENESS)
        payload, _ = protocol.read_var_bytes(welcome, 1)
        self.assertEqual(protocol.awareness_client_states(payload), [(111, True)])

        # When A disconnects abruptly, the others are told A left.
        await a.ws.disconnect()
        left = await b.ws.receive_from(timeout=2)
        payload, _ = protocol.read_var_bytes(left, 1)
        self.assertEqual(protocol.awareness_client_states(payload), [(111, False)])
        await b.ws.disconnect()
        await c.ws.disconnect()


    async def test_clock_zero_presence_then_disconnect_releases_room(self):
        """Regression: a browser's first presence message has clock 0 and is
        ignored by the protocol; disconnecting afterwards must not crash and
        must still save + release the room."""
        rooms_module.SAVE_DELAY_SECONDS = 60
        a = YClient(self.owner, self.document.id)
        await a.connect()
        await a.ws.send_to(bytes_data=self.awareness_message(222, 0, "{}"))
        await a.insert(0, "kept")
        await asyncio.sleep(0.05)
        with self.assertNoLogs("collaboration.consumers", level="ERROR"):
            await a.ws.disconnect()
        self.assertEqual(len(rooms), 0)
        await database_sync_to_async(self.document.refresh_from_db)()
        self.assertEqual(text_of(bytes(self.document.yjs_state)), "kept")
        rooms_module.SAVE_DELAY_SECONDS = 2.0


class ProtocolHelpersTests(TransactionTestCase):
    def test_var_uint_round_trip(self):
        from pycrdt import Encoder

        for value in [0, 1, 127, 128, 300, 2**20, 2**35]:
            encoder = Encoder()
            encoder.write_var_uint(value)
            decoded, _ = protocol.read_var_uint(encoder.to_bytes())
            self.assertEqual(decoded, value)

    def test_truncated_bytes_raise(self):
        with self.assertRaises(ValueError):
            protocol.read_var_bytes(b"\x05ab")
