"""
WebSocket endpoint for real-time editing: ws/documents/<uuid>/

Speaks the Yjs sync protocol, so the browser can use the standard
`y-websocket` provider.

Security
--------
* The user comes from the Django session cookie (AuthMiddlewareStack).
* Access is checked on the SERVER before any document data is sent.
* We accept the socket and then close it with an application code, so the
  browser can show a clear message and stop reconnecting:
      4401 = not logged in, 4403 = no access / not found, 4413 = message too big
      4409 = your access changed (role changed, removed, or document deleted):
             the browser reconnects so the new role is checked from scratch
* Viewers (read-only) receive the document but their edits are ignored.
* Presence (awareness) is rewritten by the server: the `user` field (name,
  color) always comes from the logged-in account, and a connection may only
  update the Yjs client ids it owns.
"""
import asyncio
import json
import logging
import time

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from pycrdt import create_awareness_message, create_sync_message, create_update_message, handle_sync_message

from accounts.presence import presence_identity
from documents.access import can_edit, get_document_and_role
from documents.activity import log_edit

from . import protocol
from .rooms import rooms

logger = logging.getLogger(__name__)

CLOSE_UNAUTHENTICATED = 4401
CLOSE_FORBIDDEN = 4403
CLOSE_TOO_LARGE = 4413
CLOSE_ACCESS_CHANGED = 4409
MAX_MESSAGE_BYTES = 5 * 1024 * 1024  # 5 MB
# A browser tab normally uses ONE Yjs client id; allow a few for safety.
MAX_CLIENT_IDS_PER_CONNECTION = 4
# Write "X edited the document" to the activity log at most once a minute.
EDIT_LOG_INTERVAL_SECONDS = 60
# Keep references to fire-and-forget tasks so they are not garbage-collected.
background_tasks: set[asyncio.Task] = set()


class DocumentConsumer(AsyncWebsocketConsumer):
    room = None
    closing = False
    edit_logged_at = float("-inf")

    async def connect(self):
        self.document_id = str(self.scope["url_route"]["kwargs"]["document_id"])
        self.group_name = f"document_{self.document_id}"
        # Yjs client ids this connection owns (their presence is ours to change).
        self.awareness_client_ids: set[int] = set()
        user = self.scope.get("user")

        await self.accept()

        if not user or not user.is_authenticated:
            await self.close(code=CLOSE_UNAUTHENTICATED)
            return

        document, role = await database_sync_to_async(get_document_and_role)(user, self.document_id)
        if document is None:
            await self.close(code=CLOSE_FORBIDDEN)
            return

        self.user = user
        self.role = role
        self.presence = presence_identity(user)
        self.room = await rooms.join(self.document_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        # 1) Ask the client what it has that we don't (e.g. offline edits).
        await self.send(bytes_data=create_sync_message(self.room.ydoc))
        # 2) Tell the newcomer who is already here.
        states = list(self.room.awareness.states.keys())
        if states:
            update = self.room.awareness.encode_awareness_update(states)
            await self.send(bytes_data=create_awareness_message(update))

    async def disconnect(self, code):
        if self.room is None:
            return
        room = self.room
        self.room = None
        try:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            # Remove this user's presence and tell the others.
            ids = [cid for cid in self.awareness_client_ids if cid in room.awareness.states]
            if ids:
                room.awareness.remove_awareness_states(ids, origin=self.channel_name)
                update = room.awareness.encode_awareness_update(ids)
                await self.broadcast(create_awareness_message(update))
            for cid in self.awareness_client_ids:
                if room.awareness_owners.get(cid) == self.channel_name:
                    del room.awareness_owners[cid]
        except Exception:
            logger.exception("Error while cleaning up presence on document %s", self.document_id)
        finally:
            # Always release the room, so the document is saved and memory freed.
            await rooms.leave(room)

    async def receive(self, text_data=None, bytes_data=None):
        if self.room is None or self.closing or not bytes_data:
            return
        if len(bytes_data) > MAX_MESSAGE_BYTES:
            await self.close(code=CLOSE_TOO_LARGE)
            return
        try:
            await self.handle_message(bytes_data)
        except Exception:
            logger.warning("Invalid Yjs message on document %s", self.document_id, exc_info=True)

    async def handle_message(self, message: bytes):
        message_type = message[0]

        if message_type == protocol.MSG_SYNC:
            await self.handle_sync(message[1:])
        elif message_type == protocol.MSG_AWARENESS:
            await self.handle_awareness(message)
        elif message_type == protocol.MSG_QUERY_AWARENESS:
            states = list(self.room.awareness.states.keys())
            if states:
                update = self.room.awareness.encode_awareness_update(states)
                await self.send(bytes_data=create_awareness_message(update))
        # MSG_AUTH and unknown types are ignored.

    async def handle_sync(self, payload: bytes):
        sync_type = payload[0]

        if sync_type == protocol.SYNC_STEP1:
            # The client tells us what it has; reply with what it is missing.
            reply = handle_sync_message(payload, self.room.ydoc)
            if reply:
                await self.send(bytes_data=reply)
            return

        if sync_type in (protocol.SYNC_STEP2, protocol.SYNC_UPDATE):
            update, _ = protocol.read_var_bytes(payload, 1)
            if update == protocol.EMPTY_UPDATE:
                return
            if not can_edit(self.role):
                # Read-only users (Sprint 5) may not change the document.
                return
            self.room.ydoc.apply_update(update)
            self.room.mark_dirty()
            await self.broadcast(create_update_message(update))
            await self.log_edit_activity()

    async def log_edit_activity(self):
        now = time.monotonic()
        if now - self.edit_logged_at < EDIT_LOG_INTERVAL_SECONDS:
            return
        self.edit_logged_at = now
        # In the background: relaying live edits should not wait for a
        # database write.
        task = asyncio.create_task(self.write_edit_log())
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    async def write_edit_log(self):
        try:
            await database_sync_to_async(log_edit)(self.document_id, self.user)
        except Exception:
            logger.exception("Could not log edit activity on document %s", self.document_id)

    async def handle_awareness(self, message: bytes):
        payload, _ = protocol.read_var_bytes(message, 1)
        entries = []
        for client_id, clock, state_json in protocol.parse_awareness_update(payload):
            if not self.claim_client_id(client_id):
                continue  # someone else's presence: not ours to change
            state = self.trusted_state(state_json)
            if state is not None:
                entries.append((client_id, clock, state))
        if not entries:
            return
        clean = protocol.encode_awareness_update(entries)
        self.room.awareness.apply_awareness_update(clean, origin=self.channel_name)
        await self.broadcast(create_awareness_message(clean))

    def claim_client_id(self, client_id: int) -> bool:
        """True if this connection owns `client_id` (claiming it if it is free)."""
        owner = self.room.awareness_owners.get(client_id)
        if owner == self.channel_name:
            return True
        if owner is not None or len(self.awareness_client_ids) >= MAX_CLIENT_IDS_PER_CONNECTION:
            return False
        self.room.awareness_owners[client_id] = self.channel_name
        self.awareness_client_ids.add(client_id)
        return True

    def trusted_state(self, state_json: str) -> str | None:
        """
        Replace the `user` field with the identity of the logged-in account.
        Keeps everything else (e.g. the cursor position). Returns None for an
        invalid state, which is then dropped.
        """
        try:
            state = json.loads(state_json)
        except ValueError:
            return None
        if state is None:
            return "null"  # the client is leaving
        if not isinstance(state, dict):
            return None
        state["user"] = self.presence
        return json.dumps(state, separators=(",", ":"))

    async def access_changed(self, event):
        """Sent by the REST API when sharing changes (documents/access.py)."""
        if self.room is None or self.closing:
            return
        if event["user_id"] is None or event["user_id"] == self.user.id:
            # Stop accepting anything with the old role, then ask the browser
            # to reconnect: connect() checks the NEW role (or refuses).
            self.closing = True
            await self.close(code=CLOSE_ACCESS_CHANGED)

    # --- fan-out to the other users in the same document --------------------
    async def broadcast(self, data: bytes):
        await self.channel_layer.group_send(
            self.group_name,
            {"type": "yjs.message", "data": data, "sender": self.channel_name},
        )

    async def yjs_message(self, event):
        if event["sender"] != self.channel_name:
            await self.send(bytes_data=event["data"])
