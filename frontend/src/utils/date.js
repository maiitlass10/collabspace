const relative = new Intl.RelativeTimeFormat("ar", { numeric: "auto" });
const absolute = new Intl.DateTimeFormat("ar", { dateStyle: "medium", timeStyle: "short" });

const UNITS = [
  ["year", 60 * 60 * 24 * 365],
  ["month", 60 * 60 * 24 * 30],
  ["week", 60 * 60 * 24 * 7],
  ["day", 60 * 60 * 24],
  ["hour", 60 * 60],
  ["minute", 60],
];

/** "منذ 5 دقائق", "أمس", ... */
export function timeAgo(isoDate) {
  const seconds = Math.round((new Date(isoDate).getTime() - Date.now()) / 1000);
  if (Math.abs(seconds) < 45) return "الآن";
  for (const [unit, size] of UNITS) {
    if (Math.abs(seconds) >= size) return relative.format(Math.round(seconds / size), unit);
  }
  return relative.format(Math.round(seconds / 60), "minute");
}

export function fullDate(isoDate) {
  return absolute.format(new Date(isoDate));
}

/** Arabic counting: مستند واحد / مستندان / 3 مستندات / 11 مستندًا */
export function documentsCount(n) {
  if (n === 1) return "مستند واحد";
  if (n === 2) return "مستندان";
  const mod100 = n % 100;
  if (mod100 >= 3 && mod100 <= 10) return `${n} مستندات`;
  return `${n} مستندًا`;
}
