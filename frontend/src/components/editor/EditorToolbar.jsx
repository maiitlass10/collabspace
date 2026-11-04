import { useEditorState } from "@tiptap/react";

function ToolButton({ label, onClick, active = false, disabled = false, children }) {
  return (
    <button
      type="button"
      className={`tool-btn ${active ? "tool-btn--active" : ""}`}
      onMouseDown={(e) => e.preventDefault()} // keep the cursor inside the editor
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      aria-pressed={active}
      title={label}
    >
      {children}
    </button>
  );
}

export default function EditorToolbar({ editor }) {
  // Re-render the toolbar only when one of these values changes.
  const state = useEditorState({
    editor,
    selector: ({ editor: e }) => ({
      bold: e.isActive("bold"),
      italic: e.isActive("italic"),
      strike: e.isActive("strike"),
      h1: e.isActive("heading", { level: 1 }),
      h2: e.isActive("heading", { level: 2 }),
      h3: e.isActive("heading", { level: 3 }),
      bullet: e.isActive("bulletList"),
      ordered: e.isActive("orderedList"),
      quote: e.isActive("blockquote"),
      code: e.isActive("codeBlock"),
      right: e.isActive({ textAlign: "right" }),
      center: e.isActive({ textAlign: "center" }),
      left: e.isActive({ textAlign: "left" }),
      canUndo: e.can().undo(),
      canRedo: e.can().redo(),
      editable: e.isEditable,
    }),
  });

  const run = (fn) => () => fn(editor.chain().focus()).run();
  const off = !state.editable;

  return (
    <div className="editor-toolbar" role="toolbar" aria-label="أدوات التنسيق">
      <div className="tool-group">
        <ToolButton label="تراجع" onClick={run((c) => c.undo())} disabled={off || !state.canUndo}>
          ↶
        </ToolButton>
        <ToolButton label="إعادة" onClick={run((c) => c.redo())} disabled={off || !state.canRedo}>
          ↷
        </ToolButton>
      </div>
      <div className="tool-group">
        <ToolButton label="عنوان رئيسي" active={state.h1} disabled={off} onClick={run((c) => c.toggleHeading({ level: 1 }))}>
          H1
        </ToolButton>
        <ToolButton label="عنوان فرعي" active={state.h2} disabled={off} onClick={run((c) => c.toggleHeading({ level: 2 }))}>
          H2
        </ToolButton>
        <ToolButton label="عنوان صغير" active={state.h3} disabled={off} onClick={run((c) => c.toggleHeading({ level: 3 }))}>
          H3
        </ToolButton>
      </div>
      <div className="tool-group">
        <ToolButton label="غامق" active={state.bold} disabled={off} onClick={run((c) => c.toggleBold())}>
          <strong>B</strong>
        </ToolButton>
        <ToolButton label="مائل" active={state.italic} disabled={off} onClick={run((c) => c.toggleItalic())}>
          <em>I</em>
        </ToolButton>
        <ToolButton label="يتوسطه خط" active={state.strike} disabled={off} onClick={run((c) => c.toggleStrike())}>
          <s>S</s>
        </ToolButton>
      </div>
      <div className="tool-group">
        <ToolButton label="قائمة نقطية" active={state.bullet} disabled={off} onClick={run((c) => c.toggleBulletList())}>
          •≡
        </ToolButton>
        <ToolButton label="قائمة مرقّمة" active={state.ordered} disabled={off} onClick={run((c) => c.toggleOrderedList())}>
          1.≡
        </ToolButton>
        <ToolButton label="اقتباس" active={state.quote} disabled={off} onClick={run((c) => c.toggleBlockquote())}>
          ❝
        </ToolButton>
        <ToolButton label="كتلة برمجية" active={state.code} disabled={off} onClick={run((c) => c.toggleCodeBlock())}>
          {"</>"}
        </ToolButton>
      </div>
      <div className="tool-group">
        <ToolButton label="محاذاة لليمين" active={state.right} disabled={off} onClick={run((c) => c.setTextAlign("right"))}>
          ⇥
        </ToolButton>
        <ToolButton label="توسيط" active={state.center} disabled={off} onClick={run((c) => c.setTextAlign("center"))}>
          ↔
        </ToolButton>
        <ToolButton label="محاذاة لليسار" active={state.left} disabled={off} onClick={run((c) => c.setTextAlign("left"))}>
          ⇤
        </ToolButton>
      </div>
    </div>
  );
}
