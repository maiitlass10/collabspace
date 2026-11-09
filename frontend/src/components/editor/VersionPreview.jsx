import { useEffect, useMemo } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import Collaboration from "@tiptap/extension-collaboration";
import TextAlign from "@tiptap/extension-text-align";
import * as Y from "yjs";

function base64ToBytes(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return bytes;
}

/**
 * Read-only view of a saved version. The version's Yjs state is loaded into
 * a separate, temporary Y.Doc that is NOT connected to the server, so
 * previewing never changes the real document.
 */
export default function VersionPreview({ state, onReady }) {
  const ydoc = useMemo(() => {
    const doc = new Y.Doc();
    Y.applyUpdate(doc, base64ToBytes(state));
    return doc;
  }, [state]);

  useEffect(() => () => ydoc.destroy(), [ydoc]);

  const editor = useEditor(
    {
      editable: false,
      extensions: [
        StarterKit.configure({ undoRedo: false }),
        Collaboration.configure({ document: ydoc }),
        TextAlign.configure({ types: ["heading", "paragraph"] }),
      ],
      editorProps: { attributes: { class: "editor-content version-preview-content" } },
    },
    [ydoc]
  );

  useEffect(() => {
    if (!editor || !onReady) return undefined;
    onReady(editor);
    return () => onReady(null);
  }, [editor, onReady]);

  return <EditorContent editor={editor} className="version-preview" />;
}
