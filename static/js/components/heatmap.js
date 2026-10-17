// Average sign-ins per day, by weekday and hour. A real <table>, so it reads as one
// to screen readers; colour is a 5-step single-hue ramp split at quintiles.
import { h } from "../dom.js";
import { fmtHour } from "../lib/format.js";

function breakpoints(values) {
  const sorted = values.filter((v) => v > 0).sort((a, b) => a - b);
  if (!sorted.length) return [];
  return [1, 2, 3, 4].map((k) => sorted[Math.floor((sorted.length * k) / 5)] ?? sorted[sorted.length - 1]);
}

function step(value, cuts) {
  if (!value) return 0;
  return 1 + cuts.filter((cut) => value >= cut).length;
}

function describe(dayName, hour, avg) {
  return `${dayName} ${fmtHour(hour)}: ${avg ? `${avg} sign-ins a day on average` : "no sign-ins"}`;
}

export function heatmap(stats) {
  const days = stats.by_weekday;
  const hours = stats.by_hour.map((x) => x.hour);
  const cell = new Map(stats.by_weekday_hour.map((c) => [`${c.weekday}:${c.hour}`, c]));
  const cuts = breakpoints(stats.by_weekday_hour.map((c) => c.avg_per_day));
  const readout = h("p", { class: "heat-readout", "aria-live": "polite" }, "Point at a square to see its average.");

  const show = (event) => {
    const td = event.target.closest("td[data-label]");
    if (td) readout.textContent = td.dataset.label;
  };

  const table = h("table", { class: "heatmap", onmouseover: show, onfocusin: show },
    h("caption", { class: "visually-hidden" }, "Average sign-ins per day, by weekday and hour"),
    h("thead", {}, h("tr", {}, h("td", {}), hours.map((hr) => h("th", { scope: "col" }, fmtHour(hr))))),
    h("tbody", {}, days.map((d) => h("tr", {},
      h("th", { scope: "row" }, d.name.slice(0, 3)),
      hours.map((hr) => {
        const c = cell.get(`${d.weekday}:${hr}`);
        const label = describe(d.name, hr, c ? c.avg_per_day : 0);
        return h("td", { class: `heat heat-${step(c ? c.avg_per_day : 0, cuts)}`, title: label, "aria-label": label, "data-label": label },
          h("span", { class: "visually-hidden" }, c ? String(c.avg_per_day) : "0"));
      }),
    ))),
  );

  const legend = h("div", { class: "heat-legend", "aria-hidden": "true" },
    h("span", {}, "Fewer"),
    [1, 2, 3, 4, 5].map((n) => h("span", { class: `heat-swatch heat heat-${n}` })),
    h("span", {}, "More"),
    h("span", { class: "heat-swatch heat heat-0" }),
    h("span", {}, "None"),
  );

  return h("figure", { class: "heat-figure" },
    h("div", { class: "scroll-x" }, table),
    h("figcaption", { class: "heat-foot" }, legend, readout),
  );
}
