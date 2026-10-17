// The sentence at the top of the visits page: Dana's actual question, answered.
import { dayRanges, fmtCount, fmtDate, fmtHour, joinWords } from "./format.js";

export function headline(stats) {
  const { from, to } = stats.range;
  const span = from && to ? ` from ${fmtDate(from)} to ${fmtDate(to)}` : "";
  const subtitle = `${fmtCount(stats.total_visits)} visit${stats.total_visits === 1 ? "" : "s"}${span}.`;
  if (!stats.total_visits) return { title: "No visits in this period.", subtitle };
  const days = joinWords(stats.busiest_days.map((d) => `${d}s`));
  const hours = joinWords(stats.busiest_hours.map(fmtHour));
  return { title: `The lobby is busiest on ${days}, around ${hours}.`, subtitle };
}

export function gapNotice(missingDays) {
  if (!missingDays || !missingDays.length) return null;
  const spans = dayRanges(missingDays).map(([a, b]) => (a === b ? `on ${fmtDate(a)}` : `from ${fmtDate(a)} to ${fmtDate(b)}`));
  return `The lobby iPad recorded no sign-ins ${joinWords(spans)}, so totals that include those days are incomplete.`;
}
