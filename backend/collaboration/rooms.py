"""
In-memory "rooms": one shared Yjs document per open CollabSpace document.

- The first user to open a document loads its saved state from the database.
- Every edit is applied to the room's Y.Doc, so newcomers get the full,
  up-to-date content immediately.
- Changes are written to the database 2 seconds after the last edit
  (debounce), and immediately when the last user leaves.

NOTE: rooms live in the memory of ONE server process. That is fine for
development and for a single Daphne process in production. Running several
processes requires a shared store (see docs/deployment in Sprint 7).
"""
import asyncio
import logging

from channels.db import database_sync_to_async
from django.utils import timezone
from pycrdt import Awareness, Doc

from documents.models import Document

logger = logging.getLogger(__name__)

SAVE_DELAY_SECONDS = 2.0


class Room:
    def __init__(self, document_id: str, ydoc: Doc):
        self.document_id = document_id
        self.ydoc = ydoc
        self.awareness = Awareness(ydoc)
        # The server is not a participant: remove its own (empty) presence
        # entry so clients never see a phantom user.
        self.awareness.set_local_state(None)
        self.connections = 0
        self.dirty = False
        self._save_task: asyncio.Task | None = None
        self._save_lock = asyncio.Lock()

    # --- persistence ------------------------------------------------------
    def mark_dirty(self):
        """Called after every edit: (re)start the 2-second save timer."""
        self.dirty = True
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
        self._save_task = asyncio.create_task(self._save_later())

    async def _save_later(self):
        try:
            await asyncio.sleep(SAVE_DELAY_SECONDS)
        except asyncio.CancelledError:
            return
        await self.save()

    async def save(self):
        async with self._save_lock:
            if not self.dirty:
                return
            self.dirty = False
            state = self.ydoc.get_update()
            try:
                await save_document_state(self.document_id, state)
            except Exception:
                # Keep the data in memory and try again on the next edit/leave.
                self.dirty = True
                logger.exception("Failed to save document %s", self.document_id)

    async def flush(self):
        """Cancel the timer and save now (used when the last user leaves)."""
        if self._save_task and not self._save_task.done():
            self._save_task.cancel()
        await self.save()


@database_sync_to_async
def load_document_state(document_id: str) -> bytes | None:
    state = Document.objects.filter(pk=document_id).values_list("yjs_state", flat=True).first()
    return bytes(state) if state else None


@database_sync_to_async
def save_document_state(document_id: str, state: bytes) -> None:
    Document.objects.filter(pk=document_id).update(yjs_state=state, updated_at=timezone.now())


class RoomManager:
    def __init__(self):
        self._rooms: dict[str, Room] = {}
        self._lock = asyncio.Lock()

    async def join(self, document_id: str) -> Room:
        async with self._lock:
            room = self._rooms.get(document_id)
            if room is None:
                ydoc = Doc()
                state = await load_document_state(document_id)
                if state:
                    ydoc.apply_update(state)
                room = Room(document_id, ydoc)
                self._rooms[document_id] = room
            room.connections += 1
            return room

    async def leave(self, room: Room) -> None:
        async with self._lock:
            room.connections -= 1
            if room.connections > 0:
                return
            await room.flush()
            # Someone may have joined while we were saving.
            if room.connections == 0 and self._rooms.get(room.document_id) is room:
                del self._rooms[room.document_id]

    def get(self, document_id: str) -> Room | None:
        return self._rooms.get(document_id)

    def __len__(self):
        return len(self._rooms)


rooms = RoomManager()
