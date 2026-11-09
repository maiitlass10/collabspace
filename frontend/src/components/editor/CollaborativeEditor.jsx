import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Collaboration from "@tiptap/extension-collaboration";
import CollaborationCaret from "@tiptap/extension-collaboration-caret";
import TextAlign from "@tiptap/extension-text-align";
import { Placeholder } from "@tiptap/extensions";
import Spinner from "../ui/Spinner.jsx";
import EditorToolbar from "./EditorToolbar.jsx";

/**
 * Rich-text editor bound to a shared Y.Doc.
 * Every keystroke becomes a small Yjs update that y-websocket sends to Django,
 * which forwards it to everyone else editing the same document.
 *
 * CollaborationCaret shares our cursor/selection through Yjs "awareness" and
 * draws the other users' carets with their name and color. The server replaces
 * the name/color we send with the ones from our account (see consumers.py).
 */
export default function CollaborativeEditor({ ydoc, provider, user, synced }) {
  const editor = useEditor(
    {
      extensions: [
        // Yjs has its own collaborative undo/redo, so disable the default one.
        StarterKit.configure({ undoRedo: false }),
        Collaboration.configure({ document: ydoc }),
        CollaborationCaret.configure({
          provider,
          user: { id: user.id, name: user.display_name, color: user.color },
        }),
        TextAlign.configure({ types: ["heading", "paragraph"] }),
        Placeholder.configure({ placeholder: "ابدأ الكتابة هنا…" }),
      ],
      editorProps: {
        attributes: { class: "editor-content", "aria-label": "محتوى المستند" },
        // Keep the cursor clear of the fixed top bar + sticky toolbar while typing.
        scrollThreshold: { top: 140, bottom: 60, left: 0, right: 0 },
        scrollMargin: { top: 140, bottom: 60, left: 0, right: 0 },
      },
    },
    [ydoc, provider]
  );

  if (!editor) return null;

  return (
    <div className="editor-shell">
      <EditorToolbar editor={editor} />
      <div className="editor-paper">
        {!synced && (
          <div className="editor-loading">
            <Spinner size={28} />
            <span>جارٍ تحميل المحتوى…</span>
          </div>
        )}
        <EditorContent editor={editor} />
      </div>
    </div>
  );
}
