from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from wireup.renderer.core import GraphData, GraphOptions, to_graph_data

__all__ = [
    "GraphEndpointOptions",
    "GraphOptions",
    "full_page_renderer",
    "render_graph_page",
    "to_graph_data",
]

if TYPE_CHECKING:
    from wireup.ioc.container.base_container import BaseContainer


@dataclass(frozen=True)
class GraphEndpointOptions:
    base_module: str | None = None

_TITLE_PLACEHOLDER = "__WIREUP_TITLE__"
_GRAPH_DATA_PLACEHOLDER = "__WIREUP_GRAPH_DATA__"
_FULL_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__WIREUP_TITLE__</title>
  <script>
    (() => {
      const storageKey = `wireup:theme:${document.title || "wireup-graph"}`;
      const storedTheme = window.localStorage.getItem(storageKey);
      const theme = storedTheme === "light" || storedTheme === "dark" ? storedTheme : "dark";
      document.documentElement.setAttribute("data-theme", theme);
    })();
  </script>
  <style>
    :root {
      --font-ui: "Inter", "Segoe UI", sans-serif;
      --font-display: "Space Grotesk", "Segoe UI", sans-serif;
      --radius-lg: 18px;
      --radius-md: 12px;
      --radius-sm: 10px;
      --shadow: 0 24px 60px rgba(0, 0, 0, 0.24);
      --bg: #0f1321;
      --bg-elevated: #151a2b;
      --bg-panel: #1b2134;
      --bg-panel-soft: #232940;
      --bg-canvas: #0c1020;
      --ink: #edf1ff;
      --muted: #8f97b4;
      --line: rgba(151, 161, 198, 0.18);
      --line-strong: rgba(151, 161, 198, 0.28);
      --accent: #ff3d7f;
      --accent-soft: rgba(255, 61, 127, 0.16);
      --accent-strong: #36d2ff;
      --service: #2a3552;
      --factory: #243c56;
      --consumer: #2f314f;
      --config: #47305d;
      --group: #1a2237;
      --edge: #69718c;
      --edge-strong: #8a93b3;
      --detail-bg: rgba(18, 23, 38, 0.96);
      --pill-bg: rgba(255, 255, 255, 0.04);
      --button-bg: rgba(255, 255, 255, 0.06);
      --button-bg-hover: rgba(255, 255, 255, 0.11);
      --node-text: #edf1ff;
      --panel-blur: blur(18px);
    }

    html[data-theme="light"] body {
      --shadow: 0 22px 54px rgba(46, 55, 80, 0.16);
      --bg: #eef2fb;
      --bg-elevated: #f7f9ff;
      --bg-panel: rgba(255, 255, 255, 0.92);
      --bg-panel-soft: #f2f5ff;
      --bg-canvas: #f8faff;
      --ink: #1b2234;
      --muted: #68728f;
      --line: rgba(84, 97, 132, 0.14);
      --line-strong: rgba(84, 97, 132, 0.24);
      --accent: #d61d61;
      --accent-soft: rgba(214, 29, 97, 0.12);
      --accent-strong: #0f8db3;
      --service: #e7eeff;
      --factory: #e0efff;
      --consumer: #e9e5ff;
      --config: #f1e5ff;
      --group: #e7ebf5;
      --edge: #7a859f;
      --edge-strong: #58637f;
      --detail-bg: rgba(255, 255, 255, 0.97);
      --pill-bg: rgba(27, 34, 52, 0.04);
      --button-bg: rgba(27, 34, 52, 0.05);
      --button-bg-hover: rgba(27, 34, 52, 0.09);
      --node-text: #1b2234;
    }

    * {
      box-sizing: border-box;
    }

    html,
    body {
      margin: 0;
      min-height: 100%;
      font-family: var(--font-ui);
      background:
        radial-gradient(circle at top left, rgba(255, 61, 127, 0.16), transparent 22%),
        radial-gradient(circle at top right, rgba(54, 210, 255, 0.12), transparent 20%),
        linear-gradient(180deg, var(--bg-elevated) 0%, var(--bg) 100%);
      color: var(--ink);
    }

    body {
      color-scheme: dark;
    }

    html[data-theme="light"] body {
      color-scheme: light;
    }

    button,
    input,
    select {
      font: inherit;
    }

    .app-shell {
      min-height: 100vh;
      display: grid;
      grid-template-rows: 58px 1fr;
    }

    .panel {
      background: var(--bg-panel);
      border: 1px solid var(--line);
      border-radius: var(--radius-lg);
      box-shadow: var(--shadow);
      backdrop-filter: var(--panel-blur);
    }

    .topbar {
      display: grid;
      grid-template-columns: auto minmax(0, 1fr) auto;
      gap: 14px;
      align-items: center;
      padding: 0 18px;
      border-bottom: 1px solid var(--line);
      background: rgba(13, 18, 31, 0.72);
      backdrop-filter: blur(18px);
      position: sticky;
      top: 0;
      z-index: 10;
    }

    html[data-theme="light"] .topbar {
      background: rgba(245, 248, 255, 0.88);
    }

    .brand {
      display: inline-flex;
      align-items: center;
      min-width: 0;
      font-family: var(--font-display);
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--ink);
    }

    .topbar-title {
      min-width: 0;
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 10px 14px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--line-strong);
      background: var(--button-bg);
      color: var(--ink);
      overflow: hidden;
    }

    .topbar-title::before {
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: #3ddc97;
      box-shadow: 0 0 12px rgba(61, 220, 151, 0.7);
      flex: 0 0 auto;
    }

    .topbar-title span {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .topbar-actions {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      justify-self: end;
    }

    .button,
    .details-pill {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      min-height: 40px;
      border-radius: var(--radius-sm);
      border: 1px solid var(--line-strong);
      background: var(--button-bg);
      color: var(--ink);
      cursor: pointer;
      transition: background 120ms ease, border-color 120ms ease, transform 120ms ease;
    }

    .button {
      padding: 0 14px;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }

    .button:hover,
    .details-pill:hover {
      background: var(--button-bg-hover);
      border-color: rgba(255, 61, 127, 0.38);
    }

    .button-accent {
      color: #ff6f9d;
      border-color: rgba(255, 61, 127, 0.38);
      box-shadow: inset 0 0 0 1px rgba(255, 61, 127, 0.08);
    }

    .controls-menu {
      position: relative;
    }

    .controls-panel {
      position: absolute;
      top: calc(100% + 10px);
      right: 0;
      width: min(280px, calc(100vw - 32px));
      padding: 12px;
      border-radius: 14px;
      border: 1px solid var(--line-strong);
      background: var(--detail-bg);
      box-shadow: var(--shadow);
      display: grid;
      gap: 10px;
      z-index: 20;
    }

    .controls-panel[hidden] {
      display: none;
    }

    .controls-section-title {
      margin: 2px 2px -2px;
      font-size: 0.7rem;
      font-weight: 800;
      letter-spacing: 0.14em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .controls-panel .button {
      width: 100%;
      justify-content: flex-start;
      text-transform: none;
      letter-spacing: 0.02em;
      font-size: 0.86rem;
      font-weight: 600;
    }

    .workspace {
      min-height: 0;
      display: grid;
      grid-template-columns: 332px minmax(0, 1fr);
    }

    .sidebar {
      padding: 20px;
      border-right: 1px solid var(--line);
      background: rgba(18, 22, 37, 0.82);
      display: grid;
      grid-template-rows: auto auto minmax(0, 1fr);
      gap: 18px;
      min-height: 0;
    }

    html[data-theme="light"] .sidebar {
      background: rgba(248, 250, 255, 0.92);
    }

    .sidebar-section {
      border-bottom: 1px solid var(--line);
      padding-bottom: 18px;
    }

    .sidebar-section:last-child {
      border-bottom: 0;
      padding-bottom: 0;
      min-height: 0;
      display: grid;
      grid-template-rows: auto auto 1fr;
    }

    .eyebrow {
      margin: 0 0 10px;
      font-size: 0.72rem;
      font-weight: 800;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .sidebar-text {
      margin: 10px 0 0;
      line-height: 1.6;
      color: var(--muted);
    }

    .field,
    .group {
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-width: 0;
    }

    .field label,
    .group .label {
      font-size: 0.72rem;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--muted);
    }

    input[type="search"] {
      width: 100%;
      border: 1px solid var(--line-strong);
      background: var(--bg-panel-soft);
      border-radius: var(--radius-sm);
      padding: 12px 14px;
      color: var(--ink);
    }

    select {
      width: 100%;
      border: 1px solid var(--line-strong);
      background: var(--bg-panel-soft);
      border-radius: var(--radius-sm);
      padding: 12px 14px;
      color: var(--ink);
    }

    .toggle-list,
    .legend-list {
      display: grid;
      gap: 10px;
    }

    .toggle,
    .legend-pill {
      display: inline-flex;
      align-items: flex-start;
      gap: 8px;
      min-height: 40px;
      font-size: 0.92rem;
      line-height: 1.35;
      border: 1px solid var(--line-strong);
      border-radius: var(--radius-sm);
      padding: 9px 12px;
      background: var(--pill-bg);
    }

    .legend-copy {
      display: grid;
      gap: 2px;
      min-width: 0;
    }

    .legend-title {
      font-weight: 600;
      color: var(--ink);
    }

    .legend-title[data-tooltip] {
      cursor: help;
    }

    .legend-description {
      font-size: 0.9rem;
      color: var(--muted);
    }

    .toggle input {
      accent-color: var(--accent);
      margin: 2px 0 0;
    }

    .toggle-copy {
      display: grid;
      gap: 2px;
      min-width: 0;
    }

    .toggle-title {
      font-weight: 600;
      color: var(--ink);
    }

    .toggle-description {
      font-size: 0.9rem;
      color: var(--muted);
    }

    .legend-pill.service {
      background: var(--service);
    }

    .legend-pill.factory {
      background: var(--factory);
    }

    .legend-pill.consumer {
      background: var(--consumer);
    }

    .legend-pill.config {
      background: var(--config);
    }

    .legend-pill.lifetime {
      border-color: var(--line-strong);
      border-width: 2px;
    }

    .legend-pill.singleton {
      border-style: solid;
    }

    .legend-pill.scoped {
      border-style: dashed;
    }

    .legend-pill.transient {
      border-style: dotted;
    }

    .viewer {
      position: relative;
      min-height: 0;
      background:
        radial-gradient(circle at 18% 18%, rgba(54, 210, 255, 0.08), transparent 20%),
        radial-gradient(circle at 74% 16%, rgba(255, 61, 127, 0.07), transparent 22%),
        linear-gradient(180deg, rgba(255, 255, 255, 0.01), transparent 42%),
        var(--bg-canvas);
      overflow: hidden;
    }

    #cy {
      position: absolute;
      inset: 0;
    }

    .details {
      position: absolute;
      right: 20px;
      bottom: 20px;
      width: min(380px, calc(100% - 40px));
      padding: 18px;
      border-radius: 16px;
      border: 1px solid var(--line-strong);
      background: var(--detail-bg);
      box-shadow: var(--shadow);
      z-index: 2;
    }

    .details h2 {
      margin: 0 0 8px;
      font-family: var(--font-display);
      font-size: 1.08rem;
    }

    .details-subtitle {
      margin: 0 0 12px;
      font-size: 0.9rem;
      color: var(--muted);
    }

    .details-empty {
      margin: 0;
      font-size: 0.9rem;
      color: var(--muted);
    }

    .details-kind-box {
      width: 12px;
      height: 12px;
      border-radius: 3px;
      border: 1px solid rgba(0, 0, 0, 0.12);
      flex: 0 0 auto;
    }

    .details-legend {
      display: grid;
      gap: 6px;
      margin: 0 0 10px;
      font-size: 0.82rem;
      color: var(--muted);
    }

    .details-legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .details-section {
      margin: 0 0 12px;
    }

    .details-section-title {
      margin: 0 0 6px;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
      color: var(--muted);
    }

    .details-pills {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      min-height: 28px;
    }

    .details-pill {
      align-items: center;
      gap: 6px;
      min-width: 0;
      font-size: 0.82rem;
      line-height: 1.2;
      padding: 0 12px;
    }

    .details-pill.empty {
      color: var(--muted);
      cursor: default;
      background: var(--button-bg);
    }

    .details-pill.empty:hover {
      border-color: var(--line-strong);
    }

    .details-pill-swatch {
      width: 10px;
      height: 10px;
      border-radius: 999px;
      flex: 0 0 auto;
    }

    .details dl {
      margin: 0;
      display: grid;
      grid-template-columns: max-content minmax(0, 1fr);
      gap: 8px 10px;
      font-size: 0.9rem;
    }

    .details dt {
      color: var(--muted);
      white-space: nowrap;
    }

    .details dd {
      margin: 0;
      overflow-wrap: anywhere;
      word-break: break-word;
    }

    .details-meta-code {
      font-size: 0.84rem;
      line-height: 1.35;
      color: var(--muted);
      font-family: "IBM Plex Mono", "SFMono-Regular", monospace;
    }

    .details-value {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }

    .theme-button .theme-button-light,
    html[data-theme="light"] .theme-button .theme-button-dark {
      display: inline;
    }

    .theme-button .theme-button-dark,
    html[data-theme="light"] .theme-button .theme-button-light {
      display: none;
    }

    @media (max-width: 980px) {
      .topbar {
        grid-template-columns: 1fr;
        padding: 14px;
      }

      .workspace {
        grid-template-columns: 1fr;
      }

      .sidebar {
        border-right: 0;
        border-bottom: 1px solid var(--line);
      }

      .details {
        position: static;
        width: auto;
        margin: 20px;
      }

      .controls-panel {
        position: fixed;
        top: 72px;
        right: 16px;
      }
    }
  </style>
</head>
<body>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <span>Wireup Graph</span>
      </div>

      <div class="topbar-title">
        <span>__WIREUP_TITLE__</span>
      </div>

      <div class="topbar-actions">
        <div class="controls-menu">
          <button
            class="button"
            id="controls-toggle"
            type="button"
            aria-expanded="false"
            aria-controls="controls-panel"
          >
            Controls
          </button>
          <div class="controls-panel" id="controls-panel" hidden>
            <div class="controls-section-title">View</div>
            <button class="button theme-button" id="theme-toggle" type="button">
              <span class="theme-button-light">Switch to Light Mode</span>
              <span class="theme-button-dark">Switch to Dark Mode</span>
            </button>
            <div class="controls-section-title">Layout</div>
            <button class="button" id="reset-layout" type="button">Reset Layout</button>
            <button class="button" id="reset-viewport" type="button">Reset Zoom</button>
            <div class="controls-section-title">Export</div>
            <button class="button button-accent" id="export-png" type="button">Export as PNG</button>
          </div>
        </div>
      </div>
    </header>

    <div class="workspace">
      <aside class="sidebar">
        <section class="sidebar-section">
          <div class="field">
            <label for="search">Filter nodes</label>
            <input id="search" type="search" placeholder="PetCatalogService, adoption, request">
          </div>
          <div class="field" style="margin-top: 14px;">
            <label for="layout-mode">Layout</label>
            <select id="layout-mode" aria-label="Graph layout">
              <option value="dagre">Dependency flow</option>
              <option value="elk">Layered</option>
              <option value="grid">Grid</option>
              <option value="circle">Circle</option>
              <option value="concentric">Concentric</option>
              <option value="breadthfirst">Classic</option>
            </select>
          </div>
          <p class="sidebar-text">
            Explore services, factories, configuration, routes, and functions from a single graph view.
          </p>
        </section>

        <section class="sidebar-section">
          <p class="eyebrow">Options</p>
          <div class="toggle-list">
            <label class="toggle">
              <input id="toggle-config" type="checkbox" checked>
              <span class="toggle-copy">
                <span class="toggle-title">Show configuration nodes</span>
                <span class="toggle-description">Display config entries that feed the selected graph.</span>
              </span>
            </label>
            <label class="toggle">
              <input id="toggle-edge-labels" type="checkbox" checked>
              <span class="toggle-copy">
                <span class="toggle-title">Show edge labels</span>
                <span class="toggle-description">Reveal parameter names on dependency connections.</span>
              </span>
            </label>
            <label class="toggle">
              <input id="toggle-modules" type="checkbox" checked>
              <span class="toggle-copy">
                <span class="toggle-title">Group by modules</span>
                <span class="toggle-description">Cluster related nodes inside their source module groups.</span>
              </span>
            </label>
            <label class="toggle">
              <input id="toggle-empty-groups" type="checkbox" checked>
              <span class="toggle-copy">
                <span class="toggle-title">Include unused groups</span>
                <span class="toggle-description">Keep empty module containers visible in the overview.</span>
              </span>
            </label>
          </div>

          <p class="eyebrow" style="margin-top:18px;">Legend</p>
          <div class="legend-list" id="legend-list">
            <span class="legend-pill lifetime singleton">Singleton</span>
            <span class="legend-pill lifetime scoped">Scoped</span>
            <span class="legend-pill lifetime transient">Transient</span>
          </div>
        </section>
      </aside>

      <section class="viewer">
        <div id="cy"></div>
        <section class="details" id="details">
          <h2>No node selected</h2>
          <p class="details-empty">Left click for the full neighborhood. Right click for dependency paths only.</p>
        </section>
      </section>
    </div>
  </div>

  <script id="wireup-graph-data" type="application/json">__WIREUP_GRAPH_DATA__</script>
  <script src="https://cdn.jsdelivr.net/npm/cytoscape@3.30.2/dist/cytoscape.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/dagre@0.8.5/dist/dagre.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/cytoscape-dagre@2.5.0/cytoscape-dagre.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/elkjs@0.10.0/lib/elk.bundled.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/cytoscape-elk@2.3.0/dist/cytoscape-elk.js"></script>
  <script>
    const VIEWPORT_PADDING = 100;
    const GRID_SIZE = 24;
    if (typeof cytoscapeDagre === "function") {
      cytoscape.use(cytoscapeDagre);
    }
    if (typeof cytoscapeElk === "function") {
      cytoscape.use(cytoscapeElk);
    }
    const graphData = JSON.parse(document.getElementById("wireup-graph-data").textContent);
    const legendList = document.getElementById("legend-list");
    const search = document.getElementById("search");
    const layoutMode = document.getElementById("layout-mode");
    const toggleConfig = document.getElementById("toggle-config");
    const toggleEdgeLabels = document.getElementById("toggle-edge-labels");
    const toggleModules = document.getElementById("toggle-modules");
    const toggleEmptyGroups = document.getElementById("toggle-empty-groups");
    const controlsToggleButton = document.getElementById("controls-toggle");
    const controlsPanel = document.getElementById("controls-panel");
    const resetLayoutButton = document.getElementById("reset-layout");
    const resetViewportButton = document.getElementById("reset-viewport");
    const exportPngButton = document.getElementById("export-png");
    const themeToggleButton = document.getElementById("theme-toggle");
    const availableLayouts = new Set(["breadthfirst", "grid", "circle", "concentric", "dagre", "elk"]);
    const hasDagreLayout = typeof cytoscape("layout", "dagre") === "function";
    const hasElkLayout = typeof cytoscape("layout", "elk") === "function";

    if (!availableLayouts.has(layoutMode.value) && layoutMode.options.length > 0) {
      layoutMode.value = layoutMode.options[0].value;
    }

    function getInitialLayoutName() {
      if (hasDagreLayout) {
        return "dagre";
      }
      if (hasElkLayout) {
        return "elk";
      }
      return "breadthfirst";
    }

    function buildLegendItem(className, title, description, showDescription = false) {
      const escapedDescription = escapeHtml(description);
      const titleMarkup = showDescription
        ? `<span class="legend-title">${title}</span>`
        : (
            `<span class="legend-title" data-tooltip="${escapedDescription}" title="${escapedDescription}">` +
            `${title}</span>`
          );
      const descriptionMarkup = showDescription
        ? `<span class="legend-description">${description}</span>`
        : "";

      return (
        `<span class="legend-pill ${className}">` +
        `<span class="legend-copy">` +
        titleMarkup +
        descriptionMarkup +
        `</span>` +
        `</span>`
      );
    }

    function getConsumerLegendKinds() {
      const consumerNodes = graphData.nodes.filter((node) => node.kind === "consumer");
      const hasRoute = consumerNodes.some((node) => String(node.label || "").startsWith("🌐 "));
      const hasFunction = consumerNodes.some((node) => String(node.label || "").startsWith("ƒ "));

      return { hasRoute, hasFunction };
    }

    function renderLegend() {
      const staticLegend = [
        buildLegendItem("lifetime singleton", "Singleton", "Shared across the whole container."),
        buildLegendItem("lifetime scoped", "Scoped", "Created once per active request or scope."),
        buildLegendItem("lifetime transient", "Transient", "Created fresh for each injection."),
      ];
      const kinds = new Set(graphData.nodes.map((node) => node.kind));
      const dynamicLegend = [];
      const consumerKinds = getConsumerLegendKinds();

      if (kinds.has("consumer") && consumerKinds.hasFunction) {
        dynamicLegend.push(buildLegendItem("consumer", "ƒ Function", "Injected callables discovered outside routes."));
      }
      if (kinds.has("consumer") && consumerKinds.hasRoute) {
        dynamicLegend.push(buildLegendItem("consumer", "🌐 Route", "Framework entrypoints that request dependencies."));
      }
      if (kinds.has("service")) {
        dynamicLegend.push(
          buildLegendItem("service", "🐍 Class injectable", "Registered classes resolved from the container.")
        );
      }
      if (kinds.has("config")) {
        dynamicLegend.push(
          buildLegendItem("config", "⚙️ Configuration", "Config values injected into services or functions.")
        );
      }
      if (kinds.has("factory")) {
        dynamicLegend.push(
          buildLegendItem("factory", "🏭 Factory", "Factory providers that create dependency instances.")
        );
      }

      legendList.innerHTML = `${dynamicLegend.join("")}${staticLegend.join("")}`;
    }

    function getBootLayoutConfig() {
      const initialLayout = getInitialLayoutName();

      if (initialLayout === "dagre") {
        return {
          name: "dagre",
          rankDir: "LR",
          padding: VIEWPORT_PADDING,
          spacingFactor: 1.1,
          nodeSep: 40,
          rankSep: 84
        };
      }

      if (initialLayout === "elk") {
        return {
          name: "elk",
          fit: true,
          animate: false,
          padding: VIEWPORT_PADDING,
          elk: {
            algorithm: "layered",
            "elk.direction": "RIGHT",
            "elk.layered.spacing.nodeNodeBetweenLayers": "90",
            "elk.spacing.nodeNode": "36",
            "elk.edgeRouting": "ORTHOGONAL"
          }
        };
      }

      return {
        name: "breadthfirst",
        directed: true,
        padding: VIEWPORT_PADDING,
        spacingFactor: 1.15,
        animate: false,
        fit: true
      };
    }

    const nodeParentById = Object.fromEntries(
      graphData.nodes.map((node) => [node.id, node.original_parent || node.parent || null])
    );
    const aggregateEdges = (() => {
      const groupedEdges = new Map();

      graphData.edges.forEach((edge) => {
        const sourceParent = nodeParentById[edge.source];
        const targetParent = nodeParentById[edge.target];
        if (!sourceParent || !targetParent || sourceParent === targetParent) {
          return;
        }

        const key = `${sourceParent}->${targetParent}`;
        if (groupedEdges.has(key)) {
          return;
        }

        groupedEdges.set(key, {
          id: `aggregate_${groupedEdges.size}`,
          source: sourceParent,
          target: targetParent,
          label: "",
          kind: "aggregate"
        });
      });

      return [...groupedEdges.values()];
    })();
    const elements = [
      ...graphData.groups.map((group) => ({ data: group })),
      ...graphData.nodes.map((node) => ({ data: node })),
      ...graphData.edges.map((edge) => ({ data: edge })),
      ...aggregateEdges.map((edge) => ({ data: edge }))
    ];

    const cy = cytoscape({
      container: document.getElementById("cy"),
      elements,
      layout: getBootLayoutConfig(),
      wheelSensitivity: 0.15,
      style: []
    });

    const details = document.getElementById("details");
    const cyContainer = document.getElementById("cy");

    let activeNodeId = null;

    function getStoragePrefix() {
      return `wireup:positions:${document.title || "wireup-graph"}`;
    }

    function getStorageKey() {
      return `${getStoragePrefix()}:${layoutMode.value}:${toggleModules.checked ? "modules" : "flat"}`;
    }

    function getThemeStorageKey() {
      return `wireup:theme:${document.title || "wireup-graph"}`;
    }

    function getLayoutStorageKey() {
      return `wireup:layout:${document.title || "wireup-graph"}`;
    }

    function readCssVar(name) {
      return getComputedStyle(document.body).getPropertyValue(name).trim();
    }

    function applyTheme(theme) {
      document.documentElement.setAttribute("data-theme", theme);
      window.localStorage.setItem(getThemeStorageKey(), theme);
      applyCytoscapeTheme();
    }

    function setControlsOpen(isOpen) {
      controlsPanel.hidden = !isOpen;
      controlsToggleButton.setAttribute("aria-expanded", isOpen ? "true" : "false");
    }

    function applyCytoscapeTheme() {
      const ink = readCssVar("--node-text");
      const lineStrong = readCssVar("--line-strong");
      const edge = readCssVar("--edge");
      const edgeStrong = readCssVar("--edge-strong");
      const service = readCssVar("--service");
      const factory = readCssVar("--factory");
      const consumer = readCssVar("--consumer");
      const config = readCssVar("--config");
      const group = readCssVar("--group");
      const accent = readCssVar("--accent");
      const dependencyHighlight = "#36d2ff";
      const dependantHighlight = "#ffb02e";
      const edgeLabelBackground = (
        document.documentElement.getAttribute("data-theme") === "light" ? "#ffffff" : "#1b2134"
      );

      cy.style([
        {
          selector: "node",
          style: {
            "label": "data(label)",
            "text-wrap": "wrap",
            "text-max-width": 240,
            "font-family": "Inter, Segoe UI, sans-serif",
            "font-size": 13,
            "text-valign": "center",
            "text-halign": "center",
            "border-width": 1.2,
            "border-style": "solid",
            "border-color": lineStrong,
            "color": ink
          }
        },
        {
          selector: 'node[lifetime = "scoped"]',
          style: {
            "border-style": "dashed"
          }
        },
        {
          selector: 'node[lifetime = "transient"]',
          style: {
            "border-style": "dotted"
          }
        },
        {
          selector: 'node[kind = "service"]',
          style: {
            "shape": "round-rectangle",
            "width": 220,
            "height": 58,
            "background-color": service
          }
        },
        {
          selector: 'node[kind = "factory"]',
          style: {
            "shape": "round-rectangle",
            "width": 228,
            "height": 64,
            "background-color": factory
          }
        },
        {
          selector: 'node[kind = "consumer"]',
          style: {
            "shape": "round-rectangle",
            "width": 260,
            "height": 58,
            "background-color": consumer
          }
        },
        {
          selector: 'node[kind = "config"]',
          style: {
            "shape": "round-rectangle",
            "width": 118,
            "height": 44,
            "background-color": config
          }
        },
        {
          selector: 'node[kind = "group"]',
          style: {
            "shape": "round-rectangle",
            "padding": "26px",
            "font-weight": 700,
            "font-size": 15,
            "text-valign": "top",
            "text-halign": "center",
            "background-color": group,
            "border-style": "solid",
            "border-color": lineStrong,
            "color": ink
          }
        },
        {
          selector: "$node > node",
          style: {
            "text-margin-y": -12
          }
        },
        {
          selector: "edge",
          style: {
            "curve-style": "bezier",
            "width": 1.7,
            "line-color": edge,
            "target-arrow-color": edge,
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.85,
            "label": "data(display_label)",
            "font-size": 10,
            "text-background-color": edgeLabelBackground,
            "text-background-opacity": 0.94,
            "text-background-padding": 3,
            "color": ink
          }
        },
        {
          selector: 'edge[kind = "aggregate"]',
          style: {
            "width": 2.2,
            "line-color": edgeStrong,
            "target-arrow-color": edgeStrong
          }
        },
        {
          selector: ".dimmed",
          style: {
            "opacity": 0.1
          }
        },
        {
          selector: ".highlight-selected",
          style: {
            "border-color": accent,
            "border-width": 2.4,
            "opacity": 1
          }
        },
        {
          selector: ".highlight-dependency",
          style: {
            "border-color": dependencyHighlight,
            "opacity": 1
          }
        },
        {
          selector: ".highlight-dependant",
          style: {
            "border-color": dependantHighlight,
            "opacity": 1
          }
        },
        {
          selector: ".hidden",
          style: {
            "display": "none"
          }
        }
      ]).update();
    }

    function savePositions() {
      const positions = {};
      cy.nodes().forEach((node) => {
        positions[node.id()] = node.position();
      });
      window.localStorage.setItem(getStorageKey(), JSON.stringify(positions));
    }

    function snapValue(value) {
      return Math.round(value / GRID_SIZE) * GRID_SIZE;
    }

    function snapPosition(position) {
      return {
        x: snapValue(position.x),
        y: snapValue(position.y)
      };
    }

    function snapNodeToGrid(node) {
      node.position(snapPosition(node.position()));
    }

    function clearStoredPositions() {
      const prefix = `${getStoragePrefix()}:`;
      const keysToRemove = [];

      for (let index = 0; index < window.localStorage.length; index += 1) {
        const key = window.localStorage.key(index);
        if (key && key.startsWith(prefix)) {
          keysToRemove.push(key);
        }
      }

      keysToRemove.forEach((key) => {
        window.localStorage.removeItem(key);
      });
    }

    function restorePositions() {
      const raw = window.localStorage.getItem(getStorageKey());
      if (!raw) {
        return false;
      }

      try {
        const positions = JSON.parse(raw);
        cy.batch(() => {
          cy.nodes().forEach((node) => {
            const position = positions[node.id()];
            if (position && typeof position.x === "number" && typeof position.y === "number") {
              node.position(snapPosition(position));
            }
          });
        });
        cy.fit(cy.elements(":visible"), VIEWPORT_PADDING);
        return true;
      } catch {
        window.localStorage.removeItem(getStorageKey());
        return false;
      }
    }

    function getLayoutConfig() {
      if (layoutMode.value === "dagre" && hasDagreLayout) {
        return {
          name: "dagre",
          rankDir: "LR",
          padding: VIEWPORT_PADDING,
          spacingFactor: 1.1,
          nodeSep: 40,
          rankSep: 84,
          animate: false,
          fit: true
        };
      }

      if (layoutMode.value === "elk" && hasElkLayout) {
        return {
          name: "elk",
          fit: true,
          animate: false,
          padding: VIEWPORT_PADDING,
          elk: {
            algorithm: "layered",
            "elk.direction": "RIGHT",
            "elk.layered.spacing.nodeNodeBetweenLayers": "90",
            "elk.spacing.nodeNode": "36",
            "elk.edgeRouting": "ORTHOGONAL"
          }
        };
      }

      if (layoutMode.value === "grid") {
        return {
          name: "grid",
          padding: VIEWPORT_PADDING,
          avoidOverlap: true,
          fit: true,
          animate: false
        };
      }

      if (layoutMode.value === "circle") {
        return {
          name: "circle",
          padding: VIEWPORT_PADDING,
          fit: true,
          animate: false
        };
      }

      if (layoutMode.value === "concentric") {
        return {
          name: "concentric",
          padding: VIEWPORT_PADDING,
          fit: true,
          animate: false,
          avoidOverlap: true,
          minNodeSpacing: 28
        };
      }

      return {
        name: "breadthfirst",
        directed: true,
        padding: VIEWPORT_PADDING,
        spacingFactor: 1.15,
        animate: false,
        fit: true
      };
    }

    function rerunLayout() {
      window.localStorage.setItem(getLayoutStorageKey(), layoutMode.value);
      const layout = cy.layout(getLayoutConfig());
      layout.one("layoutstop", () => {
        cy.batch(() => {
          cy.nodes().forEach((node) => {
            if (node.data("kind") !== "group") {
              snapNodeToGrid(node);
            }
          });
        });
        savePositions();
      });
      layout.run();
    }

    function isAggregateOverview() {
      return toggleModules.checked && activeNodeId === null;
    }

    function applyModuleOrganization() {
      cy.batch(() => {
        cy.nodes().forEach((node) => {
          if (node.data("kind") === "group") {
            return;
          }

          const originalParent = node.data("original_parent") || null;
          const currentParent = node.parent().length ? node.parent().id() : null;
          if (toggleModules.checked) {
            if (originalParent && currentParent !== originalParent) {
              node.move({ parent: originalParent });
            }
          } else if (currentParent !== null) {
            node.move({ parent: null });
          }
        });
      });
    }

    function applyGroupVisibility() {
      if (!toggleModules.checked) {
        cy.nodes('[kind = "group"]').addClass("hidden");
        return;
      }

      cy.nodes('[kind = "group"]').removeClass("hidden");
      if (toggleEmptyGroups.checked) {
        return;
      }

      cy.nodes('[kind = "group"]').forEach((group) => {
        if (isAggregateOverview()) {
          if (group.connectedEdges().filter((edge) => !edge.hasClass("hidden")).length === 0) {
            group.addClass("hidden");
          }
          return;
        }

        const visibleChildren = group.children().filter((child) => !child.hasClass("hidden"));
        const usedChildren = visibleChildren.filter((child) => {
          return child.connectedEdges().filter((edge) => !edge.hasClass("hidden")).length > 0;
        });
        if (usedChildren.length === 0) {
          group.addClass("hidden");
        }
      });
    }

    function pruneUnusedNodes() {
      if (toggleEmptyGroups.checked || isAggregateOverview()) {
        return;
      }

      cy.nodes().forEach((node) => {
        if (node.data("kind") === "group" || node.hasClass("hidden")) {
          return;
        }
        if (node.connectedEdges().filter((edge) => !edge.hasClass("hidden")).length === 0) {
          node.addClass("hidden");
        }
      });
    }

    function applyVisibility() {
      cy.elements().removeClass("hidden");
      applyModuleOrganization();

      cy.nodes().forEach((node) => {
        if (node.data("kind") === "config" && !toggleConfig.checked) {
          node.addClass("hidden");
        }
      });

      cy.edges().forEach((edge) => {
        const isAggregate = edge.data("kind") === "aggregate";
        if (
          isAggregate !== isAggregateOverview() ||
          edge.source().hasClass("hidden") ||
          edge.target().hasClass("hidden")
        ) {
          edge.addClass("hidden");
        }
      });

      pruneUnusedNodes();
      cy.edges().forEach((edge) => {
        const isAggregate = edge.data("kind") === "aggregate";
        if (
          isAggregate !== isAggregateOverview() ||
          edge.source().hasClass("hidden") ||
          edge.target().hasClass("hidden")
        ) {
          edge.addClass("hidden");
        }
        edge.data(
          "display_label",
          toggleEdgeLabels.checked && edge.data("kind") === "dependency" ? edge.data("label") : ""
        );
      });

      cy.nodes('[kind = "group"]').removeClass("dimmed");
      applyGroupVisibility();

      const query = search.value.trim().toLowerCase();
      cy.elements().removeClass("dimmed");
      if (!query) {
        return;
      }

      const hits = cy.nodes().filter((node) => {
        return !node.hasClass("hidden") && (
          String(node.data("label") || "").toLowerCase().includes(query) ||
          String(node.data("module") || "").toLowerCase().includes(query)
        );
      });

      cy.elements().addClass("dimmed");
      hits.removeClass("dimmed");
      hits.connectedEdges().removeClass("dimmed");
      hits.connectedEdges().connectedNodes().removeClass("dimmed");
      cy.nodes('[kind = "group"]').removeClass("dimmed");
      applyGroupVisibility();
    }

    function showNeighborhood(node) {
      activeNodeId = node.id();
      applyVisibility();
      cy.elements().removeClass("dimmed highlight-selected highlight-dependency highlight-dependant");
      cy.elements().addClass("dimmed");
      cy.nodes('[kind = "group"]').removeClass("dimmed");

      const dependencies = node.predecessors();
      const dependants = node.successors();
      const dependencyNodes = dependencies.filter("node");
      const dependencyEdges = dependencies.filter("edge");
      const dependantNodes = dependants.filter("node");
      const dependantEdges = dependants.filter("edge");

      node.removeClass("dimmed");
      node.addClass("highlight-selected");
      dependencyNodes.removeClass("dimmed");
      dependencyNodes.addClass("highlight-dependency");
      dependencyEdges.removeClass("dimmed");
      dependantNodes.removeClass("dimmed");
      dependantNodes.addClass("highlight-dependant");
      dependantEdges.removeClass("dimmed");

      renderDetails(node, {
        modeLabel: null,
        dependencies: node.incomers("node"),
        dependants: node.outgoers("node"),
      });
    }

    function showDependencyPaths(node) {
      activeNodeId = node.id();
      applyVisibility();
      cy.elements().removeClass("dimmed highlight-selected highlight-dependency highlight-dependant");
      cy.elements().addClass("dimmed");
      cy.nodes('[kind = "group"]').removeClass("dimmed");

      const dependencies = node.predecessors();
      const dependencyNodes = dependencies.filter("node");
      const dependencyEdges = dependencies.filter("edge");

      node.removeClass("dimmed");
      node.addClass("highlight-selected");
      dependencyNodes.removeClass("dimmed");
      dependencyNodes.addClass("highlight-dependency");
      dependencyEdges.removeClass("dimmed");

      renderDetails(node, {
        modeLabel: "Dependency paths",
        dependencies: node.incomers("node"),
        dependants: cy.collection(),
      });
    }

    function resetFocus() {
      activeNodeId = null;
      cy.elements().removeClass("dimmed highlight-selected highlight-dependency highlight-dependant");
      applyVisibility();
      details.innerHTML = `
        <h2>No node selected</h2>
        <p class="details-empty">Left click for the full neighborhood. Right click for dependency paths only.</p>
      `;
    }

    function getKindDetails(kind) {
      if (kind === "consumer") {
        const label = String(arguments[1] || "");
        if (label.startsWith("🌐 ")) {
          return { label: "Route", color: "#ecfccb" };
        }
        if (label.startsWith("ƒ ")) {
          return { label: "Function", color: "#ecfccb" };
        }
        return { label: "Function", color: "#ecfccb" };
      }
      if (kind === "service") return { label: "Class injectable", color: "#fff7ed" };
      if (kind === "factory") return { label: "Factory", color: "#eef6ff" };
      if (kind === "config") return { label: "Configuration", color: "#f6f2ff" };
      if (kind === "group") return { label: "Module group", color: "#fef3c7" };
      return { label: kind || "Unknown", color: "#e5e7eb" };
    }

    function escapeHtml(value) {
      return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#39;");
    }

    function formatLifetime(value) {
      if (!value) return null;
      return value.charAt(0).toUpperCase() + value.slice(1);
    }

    function renderNeighborPills(nodes) {
      const uniqueNodes = [];
      const seen = new Set();
      nodes.forEach((item) => {
        if (item.isNode && item.isNode() && !seen.has(item.id())) {
          seen.add(item.id());
          uniqueNodes.push(item);
        }
      });

      if (!uniqueNodes.length) {
        return '<span class="details-pill empty">None</span>';
      }

      return uniqueNodes
        .sort((left, right) => String(left.data("label")).localeCompare(String(right.data("label"))))
        .map((item) => `
          <button class="details-pill" type="button" data-node-id="${escapeHtml(item.id())}">
            <span>${escapeHtml(String(item.data("label")).replace(/\\n/g, " "))}</span>
          </button>
        `)
        .join("");
    }

    function renderDetails(node, { modeLabel, dependencies, dependants }) {
      const kindInfo = getKindDetails(node.data("kind"), node.data("label"));
      const rows = [
        `<dt>Kind</dt><dd><span class="details-value">` +
          `<span class="details-kind-box" style="background:${kindInfo.color};"></span>` +
          `<span>${kindInfo.label}</span></span></dd>`
      ];

      const lifetime = formatLifetime(node.data("lifetime"));
      if (lifetime) {
        rows.push(`<dt>Lifetime</dt><dd>${escapeHtml(lifetime)}</dd>`);
      }
      if (node.data("module")) {
        rows.push(`<dt>Module</dt><dd class="details-meta-code">${escapeHtml(node.data("module"))}</dd>`);
      }
      if (node.data("factory_name")) {
        rows.push(`<dt>Factory</dt><dd class="details-meta-code">${escapeHtml(node.data("factory_name"))}</dd>`);
      }
      if (modeLabel) {
        rows.push(`<dt>Mode</dt><dd>${escapeHtml(modeLabel)}</dd>`);
      }

      const dependencyPills = renderNeighborPills(dependencies);
      const dependantPills = renderNeighborPills(dependants);

      details.innerHTML = `
        <h2>${escapeHtml(String(node.data("label")).replace(/\\n/g, " "))}</h2>
        <div class="details-section">
          <div class="details-section-title">Details</div>
          <dl>${rows.join("")}</dl>
        </div>
        <div class="details-section">
          <div class="details-section-title">Depends on</div>
          <div class="details-pills">${dependencyPills}</div>
        </div>
        <div class="details-section">
          <div class="details-section-title">Used by</div>
          <div class="details-pills">${dependantPills}</div>
        </div>
        <p class="details-subtitle">Select any related node below to jump across the graph.</p>
      `;
    }

    [toggleConfig, toggleEdgeLabels, toggleEmptyGroups].forEach((checkbox) => {
      checkbox.addEventListener("change", applyVisibility);
    });

    layoutMode.addEventListener("change", () => {
      clearStoredPositions();
      rerunLayout();
    });

    toggleModules.addEventListener("change", () => {
      resetFocus();
      if (!restorePositions()) {
        rerunLayout();
      }
    });

    search.addEventListener("input", applyVisibility);
    resetViewportButton.addEventListener("click", () => {
      cy.fit(cy.elements(":visible"), VIEWPORT_PADDING);
      setControlsOpen(false);
    });
    exportPngButton.addEventListener("click", () => {
      const png = cy.png({ full: true, scale: 2, bg: readCssVar("--bg-canvas") });
      const link = document.createElement("a");
      link.href = png;
      link.download = "wireup-graph.png";
      link.click();
      setControlsOpen(false);
    });
    themeToggleButton.addEventListener("click", () => {
      const nextTheme = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
      applyTheme(nextTheme);
      setControlsOpen(false);
    });
    resetLayoutButton.addEventListener("click", () => {
      clearStoredPositions();
      rerunLayout();
      setControlsOpen(false);
    });
    controlsToggleButton.addEventListener("click", () => {
      setControlsOpen(controlsPanel.hidden);
    });

    cy.on("tap", "node", (event) => {
      if (event.target.data("kind") !== "group") {
        showNeighborhood(event.target);
      }
    });
    cy.on("cxttap", "node", (event) => {
      if (event.target.data("kind") !== "group") {
        showDependencyPaths(event.target);
      }
    });
    cy.on("tap", (event) => {
      if (event.target === cy) {
        resetFocus();
      }
    });
    details.addEventListener("click", (event) => {
      const button = event.target.closest("[data-node-id]");
      if (!button) return;
      const nextNode = cy.getElementById(button.getAttribute("data-node-id"));
      if (nextNode && nextNode.length) {
        showNeighborhood(nextNode);
      }
    });
    cy.on("dragfreeon", "node", (event) => {
      snapNodeToGrid(event.target);
      savePositions();
    });
    cyContainer.addEventListener("contextmenu", (event) => {
      event.preventDefault();
    });
    document.addEventListener("click", (event) => {
      if (!controlsPanel.hidden && !event.target.closest(".controls-menu")) {
        setControlsOpen(false);
      }
    });

    const storedTheme = window.localStorage.getItem(getThemeStorageKey());
    if (storedTheme === "light" || storedTheme === "dark") {
      document.documentElement.setAttribute("data-theme", storedTheme);
    }
    const storedLayout = window.localStorage.getItem(getLayoutStorageKey());
    if (storedLayout && [...layoutMode.options].some((option) => option.value === storedLayout)) {
      layoutMode.value = storedLayout;
    }
    renderLegend();
    applyCytoscapeTheme();
    applyVisibility();
    if (!restorePositions()) {
      rerunLayout();
    }
  </script>
</body>
</html>
"""


def _escape_html(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_graph_page(container: BaseContainer, *, title: str, options: GraphEndpointOptions) -> str:
    graph_data = to_graph_data(
        container,
        options=GraphOptions(base_module=options.base_module),
    )
    return full_page_renderer(graph_data, title=title)


def full_page_renderer(graph_data: GraphData, *, title: str = "Wireup Graph") -> str:
    payload = _escape_html(json.dumps(asdict(graph_data), separators=(",", ":"), ensure_ascii=False))
    return _FULL_PAGE_TEMPLATE.replace(_TITLE_PLACEHOLDER, _escape_html(title)).replace(
        _GRAPH_DATA_PLACEHOLDER, payload
    )
