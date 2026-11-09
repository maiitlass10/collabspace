import { useEffect, useRef, useState } from "react";
import * as Y from "yjs";
import { WebsocketProvider } from "y-websocket";
import { wsUrl } from "../services/api.js";

// Close codes sent by our Django consumer (collaboration/consumers.py).
const FATAL_CLOSE_CODES = {
  4401: "انتهت جلستك. سجّل الدخول من جديد.",
  4403: "ليست لديك صلاحية الوصول إلى هذا المستند.",
  4413: "التعديل أكبر من الحجم المسموح.",
};
// The owner changed our role, removed us, or deleted the document.
const ACCESS_CHANGED = 4409;

/**
 * Connects a Yjs document to the server for one CollabSpace document.
 *
 * Returns:
 *   ydoc, provider
 *   status:  "connecting" | "connected" | "disconnected"
 *   synced:  true once the initial content has been received
 *   fatalError: message when the server refused us (we stop reconnecting)
 *
 * onAccessChanged(): called when the server says our permissions changed;
 * the page then reloads the document (new role) and reconnects.
 */
export default function useCollaboration(documentId, onAccessChanged) {
  const [session, setSession] = useState(null);
  const [status, setStatus] = useState("connecting");
  const [synced, setSynced] = useState(false);
  const [fatalError, setFatalError] = useState("");
  // Keep the latest callback without reconnecting when it changes.
  const onAccessChangedRef = useRef(onAccessChanged);
  onAccessChangedRef.current = onAccessChanged;

  useEffect(() => {
    const ydoc = new Y.Doc();
    // Connects to ws(s)://<host>/ws/documents/<documentId>
    const provider = new WebsocketProvider(wsUrl("/ws/documents"), documentId, ydoc, {
      connect: false, // connect below, after React has settled
      maxBackoffTime: 5000, // retry at least every 5 seconds when offline
    });
    // In development React mounts components twice (StrictMode). Connecting on
    // the next tick means the throw-away first mount never opens a socket.
    const connectTimer = setTimeout(() => provider.connect(), 0);

    setSession({ ydoc, provider });
    setStatus("connecting");
    setSynced(false);
    setFatalError("");

    const onStatus = ({ status: next }) => setStatus(next);
    const onSync = (isSynced) => {
      if (isSynced) setSynced(true);
    };
    const onClose = (event) => {
      if (event?.code === ACCESS_CHANGED) {
        provider.disconnect(); // the page decides what happens next
        onAccessChangedRef.current?.();
        return;
      }
      const message = event && FATAL_CLOSE_CODES[event.code];
      if (message) {
        provider.disconnect(); // stop the automatic reconnect loop
        setFatalError(message);
      }
    };

    provider.on("status", onStatus);
    provider.on("sync", onSync);
    provider.on("connection-close", onClose);

    return () => {
      clearTimeout(connectTimer);
      provider.off("status", onStatus);
      provider.off("sync", onSync);
      provider.off("connection-close", onClose);
      provider.destroy();
      ydoc.destroy();
    };
  }, [documentId]);

  return {
    ydoc: session?.ydoc ?? null,
    provider: session?.provider ?? null,
    status,
    synced,
    fatalError,
  };
}
