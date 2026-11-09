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
        from pycrdt import create_awareness_message

        return create_awareness_message(protocol.encode_awareness_update([(client_id, clock, state_json)]))

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

    def test_our_var_uint_matches_pycrdt(self):
        from pycrdt import Encoder

        for value in [0, 1, 127, 128, 300, 2**20, 2**35]:
            encoder = Encoder()
            encoder.write_var_uint(value)
            self.assertEqual(protocol.write_var_uint(value), encoder.to_bytes())

    def test_arabic_awareness_round_trip(self):
        entries = [(7, 3, '{"user":{"name":"مالك"}}'), (8, 1, "null")]
        encoded = protocol.encode_awareness_update(entries)
        self.assertEqual(protocol.parse_awareness_update(encoded), entries)

    def test_truncated_bytes_raise(self):
        with self.assertRaises(ValueError):
            protocol.read_var_bytes(b"\x05ab")


class PresenceSecurityTests(TransactionTestCase):
    """Sprint 4: the server decides who you are in the editor."""

    def setUp(self):
        rooms._rooms.clear()
        self.owner = User.objects.create_user(email="o@example.com", password="x", display_name="مالك")
        self.document = Document.objects.create(owner=self.owner, title="Doc")
        self.message = AwarenessTests.awareness_message

    @staticmethod
    def states_in(message: bytes) -> dict:
        """{client_id: state_dict_or_None} from an awareness message."""
        import json

        assert message[0] == protocol.MSG_AWARENESS
        payload, _ = protocol.read_var_bytes(message, 1)
        return {cid: json.loads(state) for cid, _clock, state in protocol.parse_awareness_update(payload)}

    async def connected_pair(self):
        a = YClient(self.owner, self.document.id)
        b = YClient(self.owner, self.document.id)
        await a.connect()
        await b.connect()
        return a, b

    async def test_name_and_color_come_from_the_account(self):
        from accounts.presence import presence_color

        a, b = await self.connected_pair()
        fake = '{"user":{"name":"المدير","color":"#000000","id":999},"cursor":{"anchor":1}}'
        await a.ws.send_to(bytes_data=self.message(111, 1, fake))

        state = self.states_in(await b.ws.receive_from(timeout=2))[111]
        expected = {"id": self.owner.pk, "name": "مالك", "color": presence_color(self.owner)}
        self.assertEqual(state["user"], expected, "the claimed identity is replaced")
        self.assertEqual(state["cursor"], {"anchor": 1}, "other fields (the cursor) are kept")

        # Newcomers are also told the trusted identity, not the fake one.
        c = YClient(self.owner, self.document.id)
        await c.connect()
        self.assertEqual(self.states_in(c.pending[0])[111]["user"], expected)
        for client in (a, b, c):
            await client.ws.disconnect()

    async def test_cannot_overwrite_another_connections_presence(self):
        a, b = await self.connected_pair()
        await a.ws.send_to(bytes_data=self.message(111, 1, '{"cursor":"a"}'))
        await b.ws.receive_from(timeout=2)

        # B pretends to be A's client id: ignored, nothing is broadcast.
        await b.ws.send_to(bytes_data=self.message(111, 2, '{"cursor":"hijacked"}'))
        self.assertTrue(await a.ws.receive_nothing(timeout=0.2))
        room = rooms.get(str(self.document.id))
        self.assertEqual(room.awareness.states[111]["cursor"], "a")

        # B pretending A left is ignored too.
        await b.ws.send_to(bytes_data=self.message(111, 3, "null"))
        self.assertTrue(await a.ws.receive_nothing(timeout=0.2))
        self.assertIn(111, room.awareness.states)
        await a.ws.disconnect()
        await b.ws.disconnect()

    async def test_client_id_is_released_on_disconnect(self):
        a, b = await self.connected_pair()
        await a.ws.send_to(bytes_data=self.message(111, 1, "{}"))
        await b.ws.receive_from(timeout=2)
        await a.ws.disconnect()
        await b.ws.receive_from(timeout=2)  # "A left"
        room = rooms.get(str(self.document.id))
        self.assertNotIn(111, room.awareness_owners)
        await b.ws.disconnect()

    async def test_invalid_presence_is_dropped(self):
        a, b = await self.connected_pair()
        await a.ws.send_to(bytes_data=self.message(111, 1, "not json"))
        await a.ws.send_to(bytes_data=self.message(112, 1, "[1, 2]"))
        self.assertTrue(await b.ws.receive_nothing(timeout=0.2))
        await a.ws.disconnect()
        await b.ws.disconnect()

    async def test_limit_on_client_ids_per_connection(self):
        from .consumers import MAX_CLIENT_IDS_PER_CONNECTION

        a, b = await self.connected_pair()
        for i in range(MAX_CLIENT_IDS_PER_CONNECTION):
            await a.ws.send_to(bytes_data=self.message(500 + i, 1, "{}"))
            await b.ws.receive_from(timeout=2)
        await a.ws.send_to(bytes_data=self.message(999, 1, "{}"))
        self.assertTrue(await b.ws.receive_nothing(timeout=0.2))
        await a.ws.disconnect()
        await b.ws.disconnect()


class PresenceColorTests(TransactionTestCase):
    def test_color_is_stable_and_valid(self):
        import re

        from accounts.presence import PRESENCE_COLORS, presence_color

        user = User.objects.create_user(email="c@example.com", password="x", display_name="C")
        self.assertEqual(presence_color(user), presence_color(user))
        for color in PRESENCE_COLORS:
            self.assertRegex(color, re.compile(r"^#[0-9a-f]{6}$"))


class SharedEditingTests(TransactionTestCase):
    """Sprint 5: roles are enforced on the WebSocket, and changes apply at once."""

    def setUp(self):
        from documents.models import DocumentAccess

        rooms._rooms.clear()
        rooms_module.SAVE_DELAY_SECONDS = 0.05
        self.owner = User.objects.create_user(email="o@example.com", password="x", display_name="Owner")
        self.viewer = User.objects.create_user(email="v@example.com", password="x", display_name="Viewer")
        self.editor = User.objects.create_user(email="e@example.com", password="x", display_name="Editor")
        self.document = Document.objects.create(owner=self.owner, title="Doc")
        self.viewer_access = DocumentAccess.objects.create(document=self.document, user=self.viewer, role="viewer")
        self.editor_access = DocumentAccess.objects.create(document=self.document, user=self.editor, role="editor")

    def tearDown(self):
        rooms_module.SAVE_DELAY_SECONDS = 2.0

    async def test_editor_edits_reach_others_and_are_saved(self):
        owner = YClient(self.owner, self.document.id)
        editor = YClient(self.editor, self.document.id)
        await owner.connect()
        await editor.connect()
        await editor.insert(0, "من المحرّر")
        await owner.receive_update()
        self.assertEqual(str(owner.text), "من المحرّر")
        await owner.ws.disconnect()
        await editor.ws.disconnect()
        await database_sync_to_async(self.document.refresh_from_db)()
        self.assertEqual(text_of(bytes(self.document.yjs_state)), "من المحرّر")

    async def test_viewer_receives_content_but_cannot_change_it(self):
        owner = YClient(self.owner, self.document.id)
        viewer = YClient(self.viewer, self.document.id)
        await owner.connect()
        await viewer.connect()

        await owner.insert(0, "original")
        await viewer.receive_update()
        self.assertEqual(str(viewer.text), "original", "viewers see live edits")

        await viewer.insert(0, "HACK ")  # a tampered browser sends an edit anyway
        self.assertTrue(await owner.ws.receive_nothing(timeout=0.2), "not broadcast")
        room = rooms.get(str(self.document.id))
        self.assertEqual(text_of(room.ydoc.get_update()), "original", "not applied on the server")
        await owner.ws.disconnect()
        await viewer.ws.disconnect()
        await database_sync_to_async(self.document.refresh_from_db)()
        self.assertEqual(text_of(bytes(self.document.yjs_state)), "original", "not saved")

    async def assert_closed_with(self, client, code):
        output = await client.ws.receive_output(timeout=2)
        while output["type"] != "websocket.close":
            output = await client.ws.receive_output(timeout=2)
        self.assertEqual(output["code"], code)

    async def test_removed_member_is_disconnected_immediately(self):
        from documents.access import notify_access_changed

        viewer = YClient(self.viewer, self.document.id)
        editor = YClient(self.editor, self.document.id)
        await viewer.connect()
        await editor.connect()

        await database_sync_to_async(self.viewer_access.delete)()
        await database_sync_to_async(notify_access_changed)(self.document.id, self.viewer.id)
        await self.assert_closed_with(viewer, 4409)
        self.assertTrue(await editor.ws.receive_nothing(timeout=0.2), "others stay connected")
        await viewer.ws.disconnect()

        # Reconnecting is refused now.
        headers = await database_sync_to_async(session_headers)(self.viewer)
        ws = WebsocketCommunicator(application, f"/ws/documents/{self.document.id}/", headers=headers)
        await ws.connect()
        self.assertEqual((await ws.receive_output(timeout=2))["code"], 4403)
        await editor.ws.disconnect()

    async def test_role_change_forces_reconnect_with_new_role(self):
        from documents.access import notify_access_changed

        editor = YClient(self.editor, self.document.id)
        await editor.connect()
        self.editor_access.role = "viewer"
        await database_sync_to_async(self.editor_access.save)()
        await database_sync_to_async(notify_access_changed)(self.document.id, self.editor.id)
        await self.assert_closed_with(editor, 4409)
        await editor.ws.disconnect()

        # After reconnecting, the former editor is now read-only.
        again = YClient(self.editor, self.document.id)
        await again.connect()
        await again.insert(0, "should be ignored")
        await asyncio.sleep(0.1)
        room = rooms.get(str(self.document.id))
        self.assertEqual(text_of(room.ydoc.get_update()), "")
        await again.ws.disconnect()

    async def test_deleting_the_document_disconnects_everyone(self):
        from documents.access import notify_access_changed

        owner = YClient(self.owner, self.document.id)
        editor = YClient(self.editor, self.document.id)
        await owner.connect()
        await editor.connect()
        await database_sync_to_async(notify_access_changed)(self.document.id)
        await self.assert_closed_with(owner, 4409)
        await self.assert_closed_with(editor, 4409)
        await owner.ws.disconnect()
        await editor.ws.disconnect()

    async def test_removing_via_rest_api_disconnects_the_socket(self):
        from django.urls import reverse
        from rest_framework.test import APIClient

        viewer = YClient(self.viewer, self.document.id)
        await viewer.connect()

        def owner_removes_viewer():
            client = APIClient()
            client.force_authenticate(self.owner)
            url = reverse("document-member-detail", args=[self.document.id, self.viewer_access.pk])
            return client.delete(url).status_code

        self.assertEqual(await database_sync_to_async(owner_removes_viewer)(), 204)
        await self.assert_closed_with(viewer, 4409)
        await viewer.ws.disconnect()


class Sprint6CollaborationTests(TransactionTestCase):
    def setUp(self):
        rooms._rooms.clear()
        self.owner = User.objects.create_user(email="o@example.com", password="x", display_name="Owner")
        self.document = Document.objects.create(owner=self.owner, title="Doc")

    async def test_editing_is_logged_once_per_interval(self):
        from documents.models import ActivityLog

        a = YClient(self.owner, self.document.id)
        await a.connect()
        await a.insert(0, "one")
        await a.insert(0, "two")
        await asyncio.sleep(0.1)
        await a.ws.disconnect()
        count = await database_sync_to_async(ActivityLog.objects.filter(action="edited").count)()
        self.assertEqual(count, 1)

    async def test_snapshot_includes_edits_not_yet_saved(self):
        from documents.views import take_snapshot

        rooms_module.SAVE_DELAY_SECONDS = 60  # the normal save would not happen yet
        try:
            a = YClient(self.owner, self.document.id)
            await a.connect()
            await a.insert(0, "fresh text")
            await asyncio.sleep(0.05)
            version = await database_sync_to_async(take_snapshot)(self.document, self.owner)
            self.assertEqual(text_of(bytes(version.yjs_state)), "fresh text")
            await a.ws.disconnect()
        finally:
            rooms_module.SAVE_DELAY_SECONDS = 2.0
