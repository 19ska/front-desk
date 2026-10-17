// Plain-words formatting. Dates are split as text, never parsed with new Date(),
// so no time-zone shift can move a visit to another day.
const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July",
  "August", "September", "October", "November", "December"];

function parts(isoDate) {
  const [y, m, d] = isoDate.slice(0, 10).split("-").map(Number);
  // Day of week from the calendar date alone (UTC arithmetic, no local time zone involved).
  const weekday = (new Date(Date.UTC(y, m - 1, d)).getUTCDay() + 6) % 7;
  return { y, m, d, weekday };
}

export function fmtDate(isoDate) {
  const { y, m, d, weekday } = parts(isoDate);
  return `${DAYS[weekday].slice(0, 3)} ${d} ${MONTHS[m - 1].slice(0, 3)} ${y}`;
}

export function fmtLongDate(isoDate) {
  const { y, m, d, weekday } = parts(isoDate);
  return `${DAYS[weekday]} ${d} ${MONTHS[m - 1]} ${y}`;
}

export function fmtTime(timestamp) {
  return timestamp.slice(11, 16);
}

export function fmtDuration(minutes) {
  if (minutes === null || minutes === undefined) return "Didn't sign out";
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return h ? `${h} h ${m} min` : `${m} min`;
}

export function fmtHour(hour) {
  const suffix = hour < 12 ? "am" : "pm";
  const h = hour % 12 === 0 ? 12 : hour % 12;
  return `${h} ${suffix}`;
}

export function fmtCount(n) {
  return n.toLocaleString("en-GB");
}

export function joinWords(words) {
  if (words.length <= 1) return words.join("");
  return `${words.slice(0, -1).join(", ")} and ${words[words.length - 1]}`;
}

export function dayRanges(isoDates) {
  const ranges = [];
  for (const day of [...isoDates].sort()) {
    const last = ranges[ranges.length - 1];
    if (last && nextDay(last[1]) === day) last[1] = day;
    else ranges.push([day, day]);
  }
  return ranges;
}

function nextDay(isoDate) {
  const { y, m, d } = parts(isoDate);
  return new Date(Date.UTC(y, m - 1, d + 1)).toISOString().slice(0, 10);
}
