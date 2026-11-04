import { useCallback, useEffect, useState } from "react";
import { fetchHealth, wsUrl } from "../services/api.js";
import Button from "../components/ui/Button.jsx";

const LABELS = { loading: "جارٍ الفحص…", ok: "يعمل", error: "غير متاح" };

function StatusRow({ title, state, detail }) {
  return (
    <li className="status-row">
      <span className={`status-dot status-dot--${state}`} aria-hidden="true" />
      <span className="status-title">{title}</span>
      <span className={`status-badge status-badge--${state}`}>{LABELS[state]}</span>
      {detail && <span className="status-detail">{detail}</span>}
    </li>
  );
}

function useApiHealth() {
  const [state, setState] = useState({ status: "loading", detail: "" });
  const check = useCallback(async () => {
    setState({ status: "loading", detail: "" });
    try {
      const data = await fetchHealth();
      setState({ status: "ok", detail: `قاعدة البيانات: ${data.database_engine}` });
    } catch (error) {
      setState({ status: "error", detail: error.message });
    }
  }, []);
  useEffect(() => {
    check();
  }, [check]);
  return [state, check];
}

function useWebSocketPing() {
  const [state, setState] = useState({ status: "loading", detail: "" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    setState({ status: "loading", detail: "" });
    const socket = new WebSocket(wsUrl("/ws/ping/"));
    let sentAt = 0;
    socket.onopen = () => {
      sentAt = performance.now();
      socket.send(JSON.stringify({ type: "ping", id: 1 }));
    };
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "pong") {
        setState({ status: "ok", detail: `زمن الاستجابة: ${Math.round(performance.now() - sentAt)} ms` });
      }
    };
    socket.onerror = () => setState({ status: "error", detail: "تعذّر الاتصال" });
    return () => socket.close();
  }, [attempt]);

  return [state, () => setAttempt((n) => n + 1)];
}

export default function SystemStatusPage() {
  const [api, recheckApi] = useApiHealth();
  const [ws, recheckWs] = useWebSocketPing();

  return (
    <div className="page-container">
      <header className="page-header">
        <div>
          <h1 className="page-title">حالة النظام</h1>
          <p className="muted">فحص سريع لمكوّنات المنصة.</p>
        </div>
      </header>
      <section className="card">
        <ul className="status-list">
          <StatusRow title="الواجهة الأمامية (React + Vite)" state="ok" />
          <StatusRow title="واجهة API (Django REST)" state={api.status} detail={api.detail} />
          <StatusRow title="WebSocket (Django Channels)" state={ws.status} detail={ws.detail} />
        </ul>
        <Button
          onClick={() => {
            recheckApi();
            recheckWs();
          }}
        >
          إعادة الفحص
        </Button>
      </section>
    </div>
  );
}
