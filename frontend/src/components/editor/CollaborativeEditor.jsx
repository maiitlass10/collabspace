import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Collaboration from "@tiptap/extension-collaboration";
import TextAlign from "@tiptap/extension-text-align";
import { Placeholder } from "@tiptap/extensions";
import Spinner from "../ui/Spinner.jsx";
import EditorToolbar from "./EditorToolbar.jsx";

/**
 * Rich-text editor bound to a shared Y.Doc.
 * Every keystroke becomes a small Yjs update that y-websocket sends to Django,
 * which forwards it to everyone else editing the same document.
 */
export default function CollaborativeEditor({ ydoc, synced }) {
  const editor = useEditor(
    {
      extensions: [
        // Yjs has its own collaborative undo/redo, so disable the default one.
        StarterKit.configure({ undoRedo: false }),
        Collaboration.configure({ document: ydoc }),
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
    [ydoc]
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
