import json
from dataclasses import asdict

from wireup.renderer.core import GraphData, GraphOptions, to_graph_data

__all__ = [
    "GraphOptions",
    "full_page_renderer",
    "to_graph_data",
]

_TITLE_PLACEHOLDER = "__WIREUP_TITLE__"
_GRAPH_DATA_PLACEHOLDER = "__WIREUP_GRAPH_DATA__"
_FULL_PAGE_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>__WIREUP_TITLE__</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f3f1ea;
      --panel: rgba(255, 252, 245, 0.92);
      --ink: #1f2328;
      --muted: #5d6470;
      --line: #d3cdc1;
      --accent: #b45309;
      --service: #fff7ed;
      --factory: #eef6ff;
      --consumer: #ecfccb;
      --config: #f6f2ff;
      --shadow: 0 14px 40px rgba(60, 48, 24, 0.12);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(180, 83, 9, 0.10), transparent 28%),
        radial-gradient(circle at right center, rgba(59, 130, 246, 0.08), transparent 24%),
        linear-gradient(180deg, #f8f5ef 0%, var(--bg) 100%);
      color: var(--ink);
    }

    .shell {
      min-height: 100vh;
      padding: 20px;
    }

    .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(14px);
    }

    .topbar {
      padding: 12px 14px;
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 12px 16px;
      align-items: start;
    }

    .field,
    .group {
      display: flex;
      flex-direction: column;
      gap: 6px;
      min-width: 0;
    }

    .field.search {
      grid-column: 1 / -1;
    }

    .field label,
    .group .label {
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: var(--muted);
    }

    input[type="search"] {
      width: 100%;
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 10px;
      padding: 8px 10px;
      font: inherit;
      color: inherit;
    }

    select {
      width: 100%;
      border: 1px solid var(--line);
      background: #fff;
      border-radius: 10px;
      padding: 8px 10px;
      font: inherit;
      color: inherit;
    }

    .toggle-list,
    .legend-list {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .toggle,
    .legend-pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 0.88rem;
      white-space: nowrap;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 6px 10px;
      background: rgba(255, 255, 255, 0.8);
    }

    .toggle input {
      accent-color: var(--accent);
      margin: 0;
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
      border-color: #a39c8f;
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

    .main {
      display: grid;
      grid-template-rows: auto 1fr;
      gap: 20px;
      min-height: calc(100vh - 40px);
    }

    .viewer {
      position: relative;
      overflow: hidden;
      min-height: 720px;
    }

    #cy {
      position: absolute;
      inset: 0;
    }

    .details {
      position: absolute;
      right: 16px;
      bottom: 16px;
      width: min(320px, calc(100% - 32px));
      padding: 14px;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.94);
      box-shadow: var(--shadow);
    }

    .details h2 {
      margin: 0 0 8px;
      font-size: 1rem;
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

    .details-value {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }

    @media (max-width: 980px) {
      .topbar {
        grid-template-columns: 1fr;
        align-items: start;
      }

      .viewer {
        min-height: 70vh;
      }
    }
  </style>
</head>
<body>
  <div class="shell">
    <main class="main">
      <section class="panel topbar">
        <div class="field search">
          <label for="search">Search</label>
          <input id="search" type="search" placeholder="WeatherService, infra, request">
        </div>

        <div class="group">
          <div class="label">Layers</div>
          <div class="toggle-list">
            <label class="toggle"><input id="toggle-config" type="checkbox" checked> Configuration</label>
            <label class="toggle"><input id="toggle-edge-labels" type="checkbox"> Edge labels</label>
            <label class="toggle"><input id="toggle-modules" type="checkbox" checked> Modules</label>
            <label class="toggle"><input id="toggle-empty-groups" type="checkbox"> Unused dependencies</label>
            <button class="toggle" id="reset-layout" type="button">Reset layout</button>
          </div>
        </div>

        <div class="group">
          <div class="label">Legend</div>
          <div class="legend-list">
            <span class="legend-pill consumer">🌐 FastAPI route</span>
            <span class="legend-pill service">🐍 Class injectable</span>
            <span class="legend-pill config">⚙️ Configuration</span>
            <span class="legend-pill factory">🏭 Factory</span>
            <span class="legend-pill lifetime singleton">Singleton</span>
            <span class="legend-pill lifetime scoped">Scoped</span>
            <span class="legend-pill lifetime transient">Transient</span>
          </div>
        </div>
      </section>

      <section class="panel viewer">
        <div id="cy"></div>
        <section class="details" id="details">
          <h2>No node selected</h2>
          <p class="details-empty">Left click for the full neighborhood. Right click for dependency paths only.</p>
        </section>
      </section>
    </main>
  </div>

  <script id="wireup-graph-data" type="application/json">__WIREUP_GRAPH_DATA__</script>
  <script src="https://unpkg.com/cytoscape@3.30.2/dist/cytoscape.min.js"></script>
  <script>
    const VIEWPORT_PADDING = 100;
    const graphData = JSON.parse(document.getElementById("wireup-graph-data").textContent);
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
      layout: {
        name: "breadthfirst",
        directed: true,
        padding: VIEWPORT_PADDING,
        spacingFactor: 1.15
      },
      wheelSensitivity: 0.15,
      style: [
        {
          selector: "node",
          style: {
            "label": "data(label)",
            "text-wrap": "wrap",
            "text-max-width": 150,
            "font-family": "IBM Plex Sans, Segoe UI, sans-serif",
            "font-size": 12,
            "text-valign": "center",
            "text-halign": "center",
            "border-width": 1.2,
            "border-style": "solid",
            "border-color": "#a39c8f",
            "color": "#1f2328"
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
            "width": 158,
            "height": 54,
            "background-color": "#fff7ed"
          }
        },
        {
          selector: 'node[kind = "factory"]',
          style: {
            "shape": "round-rectangle",
            "width": 170,
            "height": 62,
            "background-color": "#eef6ff"
          }
        },
        {
          selector: 'node[kind = "consumer"]',
          style: {
            "shape": "round-rectangle",
            "width": 180,
            "height": 54,
            "background-color": "#ecfccb"
          }
        },
        {
          selector: 'node[kind = "config"]',
          style: {
            "shape": "round-rectangle",
            "width": 110,
            "height": 42,
            "background-color": "#f6f2ff"
          }
        },
        {
          selector: 'node[kind = "group"]',
          style: {
            "shape": "round-rectangle",
            "padding": "22px",
            "font-weight": 700,
            "font-size": 15,
            "text-valign": "top",
            "text-halign": "center",
            "background-color": "#fef3c7",
            "border-style": "dashed",
            "border-color": "#c39b28"
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
            "width": 2,
            "line-color": "#8b95a7",
            "target-arrow-color": "#8b95a7",
            "target-arrow-shape": "triangle",
            "arrow-scale": 0.9,
            "label": "data(display_label)",
            "font-size": 10,
            "text-background-color": "#fff",
            "text-background-opacity": 0.9,
            "text-background-padding": 2,
            "color": "#4b5563"
          }
        },
        {
          selector: 'edge[kind = "aggregate"]',
          style: {
            "width": 2.4,
            "line-color": "#6b7280",
            "target-arrow-color": "#6b7280"
          }
        },
        {
          selector: ".dimmed",
          style: {
            "opacity": 0.12
          }
        },
        {
          selector: ".highlight-selected",
          style: {
            "border-color": "#1f2328",
            "border-width": 2,
            "opacity": 1
          }
        },
        {
          selector: ".highlight-dependency",
          style: {
            "border-color": "#3D9970",
            "opacity": 1
          }
        },
        {
          selector: ".highlight-dependant",
          style: {
            "border-color": "#FFDC00",
            "opacity": 1
          }
        },
        {
          selector: ".hidden",
          style: {
            "display": "none"
          }
        }
      ]
    });

    const details = document.getElementById("details");
    const cyContainer = document.getElementById("cy");
    const search = document.getElementById("search");
    const toggleConfig = document.getElementById("toggle-config");
    const toggleEdgeLabels = document.getElementById("toggle-edge-labels");
    const toggleModules = document.getElementById("toggle-modules");
    const toggleEmptyGroups = document.getElementById("toggle-empty-groups");
    const resetLayoutButton = document.getElementById("reset-layout");

    let activeNodeId = null;

    function getStoragePrefix() {
      return `wireup:positions:${document.title || "wireup-graph"}`;
    }

    function getStorageKey() {
      return `${getStoragePrefix()}:${toggleModules.checked ? "modules" : "flat"}`;
    }

    function savePositions() {
      const positions = {};
      cy.nodes().forEach((node) => {
        positions[node.id()] = node.position();
      });
      window.localStorage.setItem(getStorageKey(), JSON.stringify(positions));
    }

    function clearStoredPositions() {
      window.localStorage.removeItem(`${getStoragePrefix()}:modules`);
      window.localStorage.removeItem(`${getStoragePrefix()}:flat`);
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
              node.position(position);
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

    function rerunLayout() {
      cy.layout({
        name: "breadthfirst",
        directed: true,
        padding: VIEWPORT_PADDING,
        spacingFactor: 1.15,
        animate: false,
        fit: true
      }).run();
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
        if (isAggregate !== isAggregateOverview() || edge.source().hasClass("hidden") || edge.target().hasClass("hidden")) {
          edge.addClass("hidden");
        }
      });

      pruneUnusedNodes();
      cy.edges().forEach((edge) => {
        const isAggregate = edge.data("kind") === "aggregate";
        if (isAggregate !== isAggregateOverview() || edge.source().hasClass("hidden") || edge.target().hasClass("hidden")) {
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

      const kindInfo = getKindDetails(node.data("kind"));
      const rows = [
        `<dt>Type</dt><dd><span class="details-value"><span class="details-kind-box" style="background:${kindInfo.color};"></span><span>${kindInfo.label}</span></span></dd>`
      ];

      if (node.data("module")) {
        rows.push(`<dt>Module</dt><dd>${node.data("module")}</dd>`);
      }
      if (node.data("factory_name")) {
        rows.push(`<dt>Factory</dt><dd>${node.data("factory_name")}</dd>`);
      }

      details.innerHTML = `
        <h2>${String(node.data("label")).replace(/\\n/g, " ")}</h2>
        <div class="details-legend">
          <span class="details-legend-item"><span>This depends on:</span><span class="details-kind-box" style="background:#3D9970;"></span></span>
          <span class="details-legend-item"><span>Depends on this:</span><span class="details-kind-box" style="background:#FFDC00;"></span></span>
        </div>
        <dl>${rows.join("")}</dl>
      `;
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

      const kindInfo = getKindDetails(node.data("kind"));
      const rows = [
        `<dt>Type</dt><dd><span class="details-value"><span class="details-kind-box" style="background:${kindInfo.color};"></span><span>${kindInfo.label}</span></span></dd>`
      ];

      if (node.data("module")) {
        rows.push(`<dt>Module</dt><dd>${node.data("module")}</dd>`);
      }
      if (node.data("factory_name")) {
        rows.push(`<dt>Factory</dt><dd>${node.data("factory_name")}</dd>`);
      }
      rows.push("<dt>Mode</dt><dd>Dependency paths</dd>");

      details.innerHTML = `
        <h2>${String(node.data("label")).replace(/\\n/g, " ")}</h2>
        <div class="details-legend">
          <span class="details-legend-item"><span>This depends on:</span><span class="details-kind-box" style="background:#3D9970;"></span></span>
        </div>
        <dl>${rows.join("")}</dl>
      `;
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
      if (kind === "service") return { label: "Class injectable", color: "#fff7ed" };
      if (kind === "factory") return { label: "Factory", color: "#eef6ff" };
      if (kind === "consumer") return { label: "Consumer", color: "#ecfccb" };
      if (kind === "config") return { label: "Configuration", color: "#f6f2ff" };
      if (kind === "group") return { label: "Module group", color: "#fef3c7" };
      return { label: kind || "Unknown", color: "#e5e7eb" };
    }

    [toggleConfig, toggleEdgeLabels, toggleEmptyGroups].forEach((checkbox) => {
      checkbox.addEventListener("change", applyVisibility);
    });

    toggleModules.addEventListener("change", () => {
      resetFocus();
      if (!restorePositions()) {
        rerunLayout();
        savePositions();
      }
    });

    search.addEventListener("input", applyVisibility);
    resetLayoutButton.addEventListener("click", () => {
      clearStoredPositions();
      rerunLayout();
      savePositions();
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
    cy.on("dragfreeon", "node", savePositions);
    cyContainer.addEventListener("contextmenu", (event) => {
      event.preventDefault();
    });

    applyVisibility();
    if (!restorePositions()) {
      rerunLayout();
      savePositions();
    }
  </script>
</body>
</html>
"""


def _escape_html(value: str) -> str:
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def full_page_renderer(graph_data: GraphData, *, title: str = "Wireup Graph") -> str:
    payload = _escape_html(json.dumps(asdict(graph_data), separators=(",", ":"), ensure_ascii=False))
    return _FULL_PAGE_TEMPLATE.replace(_TITLE_PLACEHOLDER, _escape_html(title)).replace(
        _GRAPH_DATA_PLACEHOLDER, payload
    )
