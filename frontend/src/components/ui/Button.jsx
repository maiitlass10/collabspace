import Spinner from "./Spinner.jsx";

export default function Button({
  children,
  variant = "primary",
  loading = false,
  block = false,
  type = "button",
  disabled,
  className = "",
  ...props
}) {
  const classes = ["btn", `btn-${variant}`, block ? "btn-block" : "", className]
    .filter(Boolean)
    .join(" ");

  return (
    <button type={type} className={classes} disabled={disabled || loading} {...props}>
      {loading && <Spinner size={16} />}
      <span>{children}</span>
    </button>
  );
}
