"""Standalone HTML renderer for embedumap."""

from __future__ import annotations

import json

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>__TITLE__</title>
<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; overflow: hidden; }
  body {
    font-family: system-ui, -apple-system, sans-serif;
    background: #0f172a;
    color: #e2e8f0;
  }
  #app {
    display: grid;
    grid-template-rows: auto 1fr auto;
    height: 100dvh;
  }
  #controls, #timeline-bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 12px;
    background: #111827;
    border-bottom: 1px solid #1f2937;
    flex-wrap: wrap;
  }
  #timeline-bar {
    border-top: 1px solid #1f2937;
    border-bottom: none;
  }
  .label {
    color: #94a3b8;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }
  .button-group {
    display: flex;
    gap: 4px;
    flex-wrap: wrap;
  }
  .button-group button, select, .toolbar button {
    background: #0f172a;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    font: inherit;
  }
  .button-group button.active {
    background: #2563eb;
    border-color: #2563eb;
  }
  #plot-wrap {
    position: relative;
    overflow: hidden;
  }
  #plot, #overlay {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
  }
  #overlay { cursor: crosshair; }
  #tooltip {
    position: fixed;
    pointer-events: none;
    z-index: 1000;
    display: none;
    max-width: min(360px, 90vw);
    max-height: min(520px, 80vh);
    overflow: auto;
    padding: 10px;
    border: 1px solid #334155;
    border-radius: 8px;
    background: rgba(15, 23, 42, 0.97);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.45);
  }
  #tooltip img {
    width: 100%;
    max-height: 260px;
    object-fit: contain;
    border-radius: 6px;
    background: #020617;
    margin-bottom: 8px;
  }
  .tooltip-label {
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 8px;
  }
  .tooltip-grid {
    display: grid;
    grid-template-columns: minmax(84px, auto) 1fr;
    gap: 6px 10px;
    font-size: 12px;
  }
  .tooltip-key { color: #93c5fd; }
  .tooltip-value { color: #cbd5e1; word-break: break-word; }
  #popup-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(2, 6, 23, 0.72);
    display: none;
    z-index: 180;
  }
  #popup {
    position: fixed;
    inset: 5vh 4vw;
    display: none;
    z-index: 200;
    background: #111827;
    border: 1px solid #334155;
    border-radius: 10px;
    overflow: hidden;
    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.55);
  }
  #popup.visible, #popup-backdrop.visible { display: block; }
  #popup {
    display: none;
    grid-template-rows: auto auto 1fr;
  }
  #popup.visible { display: grid; }
  .popup-head, .toolbar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 14px;
    border-bottom: 1px solid #1f2937;
    flex-wrap: wrap;
  }
  .popup-title {
    font-size: 15px;
    font-weight: 700;
  }
  .spacer { margin-left: auto; }
  #popup-body {
    overflow: auto;
    padding: 14px;
  }
  .popup-table {
    width: 100%;
    border-collapse: collapse;
  }
  .popup-table th, .popup-table td {
    border-bottom: 1px solid #1f2937;
    padding: 8px 10px;
    text-align: left;
    vertical-align: top;
    font-size: 12px;
  }
  .popup-table th {
    position: sticky;
    top: 0;
    background: #0f172a;
    color: #93c5fd;
  }
  .popup-image-list {
    display: grid;
    gap: 8px;
  }
  .popup-image-list img, .card-images img {
    width: 100%;
    max-height: 360px;
    object-fit: contain;
    border-radius: 8px;
    background: #020617;
  }
  .card-list {
    display: grid;
    gap: 14px;
  }
  .card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
    gap: 14px;
  }
  .card {
    border: 1px solid #1f2937;
    border-radius: 10px;
    background: #0f172a;
    padding: 12px;
    display: grid;
    gap: 10px;
  }
  .card-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 10px;
  }
  .card-title {
    font-size: 13px;
    font-weight: 700;
  }
  .card-subtitle {
    color: #94a3b8;
    font-size: 12px;
  }
  .card-fields {
    display: grid;
    grid-template-columns: minmax(84px, auto) 1fr;
    gap: 6px 10px;
    font-size: 12px;
  }
  .field-key { color: #93c5fd; }
  .field-value { color: #cbd5e1; word-break: break-word; }
  #timeline-wrap {
    display: none;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: min(640px, 100%);
  }
  #timeline-wrap.visible { display: flex; }
  .range-block {
    position: relative;
    flex: 1;
    height: 24px;
  }
  .range-block input[type=range] {
    position: absolute;
    inset: 0;
    width: 100%;
    background: transparent;
    pointer-events: none;
    appearance: none;
  }
  .range-block input[type=range]::-webkit-slider-thumb {
    appearance: none;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #2563eb;
    border: 2px solid #0f172a;
    pointer-events: all;
  }
  .range-block input[type=range]::-moz-range-thumb {
    width: 16px;
    height: 16px;
    border-radius: 50%;
    background: #2563eb;
    border: 2px solid #0f172a;
    pointer-events: all;
  }
  .timeline-line {
    position: absolute;
    top: 50%;
    left: 0;
    right: 0;
    height: 4px;
    transform: translateY(-50%);
    border-radius: 999px;
    background: #1f2937;
  }
  .timeline-fill {
    position: absolute;
    top: 50%;
    height: 4px;
    transform: translateY(-50%);
    border-radius: 999px;
    background: #2563eb;
  }
</style>
</head>
<body>
<div id="app">
  <div id="controls">
    <span class="label">Color</span>
    <div id="color-group" class="button-group"></div>
    <span class="label">Filter</span>
    <div id="filter-group" class="button-group"></div>
    <div class="spacer"></div>
    <div id="summary" class="label"></div>
  </div>
  <div id="plot-wrap">
    <canvas id="plot"></canvas>
    <svg id="overlay"></svg>
  </div>
  <div id="timeline-bar">
    <div id="timeline-wrap">
      <span id="timeline-start"></span>
      <div class="range-block">
        <div class="timeline-line"></div>
        <div id="timeline-fill" class="timeline-fill"></div>
        <input id="timeline-min" type="range">
        <input id="timeline-max" type="range">
      </div>
      <span id="timeline-end"></span>
    </div>
  </div>
</div>
<div id="tooltip"></div>
<div id="popup-backdrop"></div>
<div id="popup">
  <div class="popup-head">
    <div class="popup-title" id="popup-title"></div>
    <button id="popup-close">Close</button>
  </div>
  <div class="toolbar">
    <span class="label">Sort</span>
    <select id="sort-column"></select>
    <button id="sort-direction" type="button">Ascending</button>
    <span class="label">Popup</span>
    <span id="popup-style-label"></span>
  </div>
  <div id="popup-body"></div>
</div>
<script>
const DATA = __DATA__;
const $ = (selector, element = document) => element.querySelector(selector);
const PALETTE = [
  "#4e79a7","#f28e2b","#e15759","#76b7b2","#59a14f","#edc948","#b07aa1","#ff9da7",
  "#9c755f","#8dd3c7","#17becf","#aec7e8","#ffbb78","#98df8a","#ff9896","#c5b0d5",
  "#c49c94","#f7b6d2","#bcbd22","#637939","#9edae5","#5254a3","#ce6dbd","#843c39"
];
const margin = { top: 18, right: 18, bottom: 18, left: 18 };
const pointRadius = 4;
const plot = $("#plot");
const overlay = d3.select("#overlay");
const tooltip = $("#tooltip");
const popup = $("#popup");
const popupBackdrop = $("#popup-backdrop");
const popupBody = $("#popup-body");
const popupTitle = $("#popup-title");
const summary = $("#summary");
const popupStyleLabel = $("#popup-style-label");
popupStyleLabel.textContent = DATA.popupStyle;

const state = {
  colorBy: DATA.colorColumns[0] ?? "cluster",
  filters: Object.fromEntries(DATA.filterColumns.map((column) => [column, ""])),
  selectedIds: new Set(),
  sortColumn: DATA.defaultSort,
  sortAsc: true,
  timelineMin: DATA.timelineMin,
  timelineMax: DATA.timelineMax,
};

let width = 0;
let height = 0;
let dpr = window.devicePixelRatio || 1;
let xScale = d3.scaleLinear();
let yScale = d3.scaleLinear();
let quadtree = null;

const xDomain = DATA.xDomain[0] === DATA.xDomain[1]
  ? [DATA.xDomain[0] - 1, DATA.xDomain[1] + 1]
  : DATA.xDomain;
const yDomain = DATA.yDomain[0] === DATA.yDomain[1]
  ? [DATA.yDomain[0] - 1, DATA.yDomain[1] + 1]
  : DATA.yDomain;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function displaySortLabel(column) {
  if (column === "_row_index") return "Row order";
  return column;
}

function formatTimeline(ms) {
  if (ms == null) return "";
  return new Date(ms).toISOString().replace("T", " ").replace(".000Z", " UTC");
}

function currentRows() {
  return DATA.rows.filter((row) => {
    for (const [column, value] of Object.entries(state.filters)) {
      if (value && String(row.filters[column] ?? "") !== value) return false;
    }
    if (DATA.timelineColumn && row.timelineMs != null) {
      if (row.timelineMs < state.timelineMin || row.timelineMs > state.timelineMax) return false;
    }
    if (DATA.timelineColumn && row.timelineMs == null) return false;
    return true;
  });
}

function colorValue(row) {
  return row.colors[state.colorBy] ?? "(blank)";
}

function colorScale() {
  const values = [...new Set(DATA.rows.map(colorValue))];
  return d3.scaleOrdinal().domain(values).range(PALETTE);
}

function draw() {
  const rows = currentRows();
  summary.textContent = `${rows.length} visible / ${DATA.rows.length} total`;
  const ctx = plot.getContext("2d");
  ctx.clearRect(0, 0, width, height);
  const scale = colorScale();
  const selected = state.selectedIds;
  rows.forEach((row) => {
    const x = xScale(row.x);
    const y = yScale(row.y);
    ctx.beginPath();
    ctx.arc(x, y, selected.has(row.id) ? pointRadius + 1.5 : pointRadius, 0, Math.PI * 2);
    ctx.fillStyle = scale(colorValue(row));
    ctx.globalAlpha = selected.size && !selected.has(row.id) ? 0.2 : 0.9;
    ctx.fill();
  });
  ctx.globalAlpha = 1;
  quadtree = d3.quadtree()
    .x((row) => xScale(row.x))
    .y((row) => yScale(row.y))
    .addAll(rows);
}

function resize() {
  const rect = plot.parentElement.getBoundingClientRect();
  width = rect.width;
  height = rect.height;
  plot.width = Math.floor(width * dpr);
  plot.height = Math.floor(height * dpr);
  plot.style.width = `${width}px`;
  plot.style.height = `${height}px`;
  const ctx = plot.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  xScale = d3.scaleLinear().domain(xDomain).range([margin.left, width - margin.right]);
  yScale = d3.scaleLinear().domain(yDomain).range([height - margin.bottom, margin.top]);
  overlay.attr("width", width).attr("height", height);
  draw();
}

function showTooltip(row, event) {
  const image = row.images[0]
    ? `<img src="${escapeHtml(row.images[0])}" alt="${escapeHtml(row.label)}" loading="lazy" fetchpriority="low">`
    : "";
  const fields = Object.entries(row.tooltip)
    .map(([key, value]) => `<div class="tooltip-key">${escapeHtml(key)}</div><div class="tooltip-value">${escapeHtml(value)}</div>`)
    .join("");
  tooltip.innerHTML = `${image}<div class="tooltip-label">${escapeHtml(row.label)}</div><div class="tooltip-grid">${fields}</div>`;
  tooltip.style.display = "block";
  tooltip.style.left = `${Math.min(window.innerWidth - tooltip.offsetWidth - 12, event.clientX + 14)}px`;
  tooltip.style.top = `${Math.min(window.innerHeight - tooltip.offsetHeight - 12, event.clientY + 14)}px`;
}

function hideTooltip() {
  tooltip.style.display = "none";
}

function comparator(left, right) {
  const column = state.sortColumn;
  const direction = state.sortAsc ? 1 : -1;
  let a;
  let b;
  if (column === "_row_index") {
    a = left.id;
    b = right.id;
  } else if (column === DATA.timelineColumn) {
    a = left.timelineMs ?? Number.NEGATIVE_INFINITY;
    b = right.timelineMs ?? Number.NEGATIVE_INFINITY;
  } else {
    a = String(left.raw[column] ?? "");
    b = String(right.raw[column] ?? "");
  }
  if (a < b) return -1 * direction;
  if (a > b) return 1 * direction;
  return (left.id - right.id) * direction;
}

function selectedRows() {
  return DATA.rows.filter((row) => state.selectedIds.has(row.id)).sort(comparator);
}

function renderImages(row) {
  if (!row.images.length) return "";
  return `<div class="card-images popup-image-list">${row.images.map((url) => (
    `<img src="${escapeHtml(url)}" alt="${escapeHtml(row.label)}" loading="lazy" fetchpriority="low">`
  )).join("")}</div>`;
}

function renderFieldGrid(row) {
  return Object.entries(row.raw)
    .map(([key, value]) => `<div class="field-key">${escapeHtml(key)}</div><div class="field-value">${escapeHtml(value)}</div>`)
    .join("");
}

function renderTable(rows) {
  const headers = DATA.columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("");
  const body = rows.map((row) => {
    const cells = DATA.columns.map((column) => {
      const value = row.raw[column] ?? "";
      const images = DATA.imageColumns.includes(column)
        ? row.images.map((url) => `<img src="${escapeHtml(url)}" alt="${escapeHtml(row.label)}" loading="lazy" fetchpriority="low" style="width:100%;max-height:240px;object-fit:contain;background:#020617;border-radius:6px;margin-bottom:6px;">`).join("")
        : "";
      return `<td>${images}${escapeHtml(value)}</td>`;
    }).join("");
    return `<tr>${cells}</tr>`;
  }).join("");
  popupBody.innerHTML = `<table class="popup-table"><thead><tr>${headers}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderCards(rows, grid) {
  const className = grid ? "card-grid" : "card-list";
  popupBody.innerHTML = `<div class="${className}">${rows.map((row) => `
    <article class="card">
      <div class="card-head">
        <div class="card-title">${escapeHtml(row.label)}</div>
        <div class="card-subtitle">${escapeHtml(row.timelineText ?? row.clusterLabel)}</div>
      </div>
      ${renderImages(row)}
      <div class="card-fields">${renderFieldGrid(row)}</div>
    </article>
  `).join("")}</div>`;
}

function renderPopup() {
  const rows = selectedRows();
  if (!rows.length) {
    popup.classList.remove("visible");
    popupBackdrop.classList.remove("visible");
    return;
  }
  popupTitle.textContent = `${rows.length} row${rows.length === 1 ? "" : "s"} selected`;
  if (DATA.popupStyle === "table") {
    renderTable(rows);
  } else if (DATA.popupStyle === "grid") {
    renderCards(rows, true);
  } else {
    renderCards(rows, false);
  }
  popup.classList.add("visible");
  popupBackdrop.classList.add("visible");
}

function dismissPopup() {
  popup.classList.remove("visible");
  popupBackdrop.classList.remove("visible");
}

function buildColorControls() {
  const group = $("#color-group");
  group.innerHTML = DATA.colorColumns.map((column) => (
    `<button data-color="${escapeHtml(column)}" class="${column === state.colorBy ? "active" : ""}">${escapeHtml(displaySortLabel(column))}</button>`
  )).join("");
  group.addEventListener("click", (event) => {
    const button = event.target.closest("[data-color]");
    if (!button) return;
    state.colorBy = button.dataset.color;
    for (const candidate of group.querySelectorAll("button")) {
      candidate.classList.toggle("active", candidate === button);
    }
    draw();
  });
}

function buildFilterControls() {
  const container = $("#filter-group");
  container.innerHTML = DATA.filterColumns.map((column) => {
    const values = [...new Set(DATA.rows.map((row) => String(row.filters[column] ?? "(blank)")))].sort();
    const options = [`<option value="">All ${escapeHtml(column)}</option>`].concat(
      values.map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`)
    ).join("");
    return `<select data-filter="${escapeHtml(column)}">${options}</select>`;
  }).join("");
  for (const select of container.querySelectorAll("select")) {
    select.addEventListener("change", (event) => {
      state.filters[event.target.dataset.filter] = event.target.value;
      draw();
    });
  }
}

function buildSortControls() {
  const select = $("#sort-column");
  select.innerHTML = DATA.sortColumns.map((column) => (
    `<option value="${escapeHtml(column)}"${column === state.sortColumn ? " selected" : ""}>${escapeHtml(displaySortLabel(column))}</option>`
  )).join("");
  select.addEventListener("change", (event) => {
    state.sortColumn = event.target.value;
    renderPopup();
  });
  $("#sort-direction").addEventListener("click", () => {
    state.sortAsc = !state.sortAsc;
    $("#sort-direction").textContent = state.sortAsc ? "Ascending" : "Descending";
    renderPopup();
  });
}

function buildTimelineControls() {
  if (!DATA.timelineColumn || DATA.timelineMin == null || DATA.timelineMax == null) return;
  $("#timeline-wrap").classList.add("visible");
  const minInput = $("#timeline-min");
  const maxInput = $("#timeline-max");
  minInput.min = DATA.timelineMin;
  minInput.max = DATA.timelineMax;
  minInput.value = DATA.timelineMin;
  maxInput.min = DATA.timelineMin;
  maxInput.max = DATA.timelineMax;
  maxInput.value = DATA.timelineMax;

  const syncLabels = () => {
    state.timelineMin = Math.min(Number(minInput.value), Number(maxInput.value));
    state.timelineMax = Math.max(Number(minInput.value), Number(maxInput.value));
    $("#timeline-start").textContent = formatTimeline(state.timelineMin);
    $("#timeline-end").textContent = formatTimeline(state.timelineMax);
    const full = DATA.timelineMax - DATA.timelineMin || 1;
    const left = ((state.timelineMin - DATA.timelineMin) / full) * 100;
    const right = ((state.timelineMax - DATA.timelineMin) / full) * 100;
    $("#timeline-fill").style.left = `${left}%`;
    $("#timeline-fill").style.width = `${right - left}%`;
    draw();
  };
  minInput.addEventListener("input", syncLabels);
  maxInput.addEventListener("input", syncLabels);
  syncLabels();
}

function bindInteractions() {
  $("#popup-close").addEventListener("click", dismissPopup);
  popupBackdrop.addEventListener("click", dismissPopup);

  $("#plot-wrap").addEventListener("mousemove", (event) => {
    if (!quadtree) return;
    const rect = plot.getBoundingClientRect();
    const found = quadtree.find(event.clientX - rect.left, event.clientY - rect.top, 12);
    if (!found) {
      hideTooltip();
      return;
    }
    showTooltip(found, event);
  });
  $("#plot-wrap").addEventListener("mouseleave", hideTooltip);
  $("#plot-wrap").addEventListener("click", (event) => {
    if (!quadtree) return;
    const rect = plot.getBoundingClientRect();
    const found = quadtree.find(event.clientX - rect.left, event.clientY - rect.top, 12);
    state.selectedIds = new Set(found ? [found.id] : []);
    draw();
    renderPopup();
  });

  const brush = d3.brush().on("end", ({ selection }) => {
    if (!selection) {
      state.selectedIds = new Set();
      draw();
      dismissPopup();
      return;
    }
    const [[x0, y0], [x1, y1]] = selection;
    const selected = currentRows()
      .filter((row) => {
        const x = xScale(row.x);
        const y = yScale(row.y);
        return x >= x0 && x <= x1 && y >= y0 && y <= y1;
      })
      .map((row) => row.id);
    state.selectedIds = new Set(selected);
    overlay.select(".brush").call(brush.move, null);
    draw();
    renderPopup();
  });
  overlay.append("g").attr("class", "brush").call(brush);
}

buildColorControls();
buildFilterControls();
buildSortControls();
buildTimelineControls();
bindInteractions();
resize();
window.addEventListener("resize", resize);
</script>
</body>
</html>
"""


def render_html(payload: dict[str, object]) -> str:
    """Embed the payload into a standalone HTML page."""

    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return HTML_TEMPLATE.replace("__TITLE__", str(payload["title"])).replace("__DATA__", data_json)
