import { useCallback, useEffect, useState } from "react";
import { documentsApi } from "../../services/documents.js";
import { describeActivity } from "../../utils/activity.js";
import { fullDate, timeAgo } from "../../utils/date.js";
import Avatar from "../ui/Avatar.jsx";
import Button from "../ui/Button.jsx";
import Modal from "../ui/Modal.jsx";
import Spinner from "../ui/Spinner.jsx";

/** "Who did what, and when" for one document. Visible to every member. */
export default function ActivityPanel({ open, documentId, onClose }) {
  const [items, setItems] = useState([]);
  const [nextPage, setNextPage] = useState(null);
  const [status, setStatus] = useState("loading"); // loading | ready | error
  const [error, setError] = useState("");
  const [loadingMore, setLoadingMore] = useState(false);

  const load = useCallback(
    async (page = 1) => {
      if (page === 1) setStatus("loading");
      else setLoadingMore(true);
      try {
        const data = await documentsApi.activity(documentId, page);
        setItems((current) => (page === 1 ? data.results : [...current, ...data.results]));
        setNextPage(data.next ? page + 1 : null);
        setStatus("ready");
      } catch (err) {
        setError(err.message);
        setStatus("error");
      } finally {
        setLoadingMore(false);
      }
    },
    [documentId]
  );

  useEffect(() => {
    if (open) load();
  }, [open, load]);

  return (
    <Modal open={open} title="سجل النشاط" onClose={onClose}>
      {status === "loading" && (
        <div className="text-center">
          <Spinner size={24} />
        </div>
      )}
      {status === "error" && <p className="field-error">{error}</p>}
      {status === "ready" && items.length === 0 && <p className="muted">لا يوجد نشاط بعد.</p>}
      {status === "ready" && items.length > 0 && (
        <ol className="activity-list">
          {items.map((item) => {
            const { icon, text } = describeActivity(item);
            const name = item.actor?.display_name || "مستخدم محذوف";
            return (
              <li key={item.id} className="activity-item">
                <Avatar name={name} color={item.actor?.color} size={32} />
                <div className="activity-body">
                  <p>
                    <strong>{name}</strong> {text}
                  </p>
                  <time className="activity-time" dateTime={item.created_at} title={fullDate(item.created_at)}>
                    {icon} {timeAgo(item.created_at)}
                  </time>
                </div>
              </li>
            );
          })}
        </ol>
      )}
      {nextPage && (
        <div className="text-center">
          <Button variant="secondary" loading={loadingMore} onClick={() => load(nextPage)}>
            عرض المزيد
          </Button>
        </div>
      )}
    </Modal>
  );
}
