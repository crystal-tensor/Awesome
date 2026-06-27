import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  AlertCircle,
  BellRing,
  Bot,
  CheckCircle2,
  CircleDollarSign,
  DatabaseZap,
  FileText,
  Link2,
  LocateFixed,
  Network,
  Newspaper,
  PlayCircle,
  RefreshCw,
  RotateCcw,
  Satellite,
  Target
} from "lucide-react";
import { SiteTopNav } from "./portalHome.jsx";

const typeLabels = {
  all: "全部资产",
  equity: "股指",
  fx: "外汇",
  rates: "利率",
  commodity: "商品",
  crypto: "加密"
};

const regionLabels = {
  global: "全球",
  americas: "美洲",
  emea: "欧洲 / 中东",
  apac: "亚太"
};

const tabLabels = {
  all: "全部",
  risk: "风险",
  flow: "资金",
  news: "信息"
};

const typeColors = {
  equity: "#2f7df6",
  fx: "#22d3ee",
  rates: "#f59e0b",
  commodity: "#34d399",
  crypto: "#a78bfa",
  hub: "#77849a"
};

const relationLabels = {
  contains: "归属",
  "discount-rate": "折现率",
  "real-rate": "实际利率",
  "dollar-sensitive": "美元敏感",
  liquidity: "流动性",
  "commodity-beta": "商品贝塔",
  "growth-demand": "增长需求",
  "risk-appetite": "风险偏好",
  dominance: "主导资产",
  "china-link": "中国链路",
  "yen-link": "日元链路",
  "global-beta": "全球贝塔"
};

const signalIds = new Set(["spx", "nasdaq", "ust10y", "dxy", "gold", "crude", "btc", "hsi", "shcomp"]);
const WORLD_BOUNDS = [
  [-58, -171],
  [74, 171]
];

function useEChart(option, deps) {
  const ref = useRef(null);
  const chartRef = useRef(null);

  useEffect(() => {
    if (!ref.current) return undefined;
    chartRef.current = echarts.init(ref.current);
    return () => {
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    if (chartRef.current && option) {
      chartRef.current.setOption(option, true);
    }
  }, deps);

  useEffect(() => {
    const onResize = () => chartRef.current?.resize();
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  return ref;
}

function formatPrice(node) {
  if (node?.price === null || node?.price === undefined || Number.isNaN(Number(node.price))) return "-";
  const value = Number(node.price);
  if (node.type === "rates") return `${(value / 10).toFixed(2)}%`;
  if (node.type === "fx") return value.toFixed(4);
  if (value >= 1000) return value.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (value >= 100) return value.toFixed(2);
  return value.toFixed(3);
}

function formatChange(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  const numeric = Number(value);
  return `${numeric > 0 ? "+" : ""}${numeric.toFixed(2)}%`;
}

function formatTime(value) {
  if (!value) return "-";
  return new Intl.DateTimeFormat("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  }).format(new Date(value));
}

function changeClass(value) {
  if (!Number.isFinite(Number(value))) return "flat";
  return Number(value) >= 0 ? "up" : "down";
}

function toneLabel(tone) {
  if (tone === "risk-on") return "风险偏好升温";
  if (tone === "risk-off") return "风险偏好降温";
  return "多空混合";
}

function regionBucket(node) {
  if (node.region === "Americas") return "americas";
  if (node.region === "Europe" || node.region === "FX" || node.region === "Rates" || node.region === "Commodities") return "emea";
  if (node.region === "Asia Pacific" || node.region === "China / HK" || node.region === "Crypto") return "apac";
  return "global";
}

function tabMatch(tab, node) {
  if (tab === "all") return true;
  if (tab === "risk") return ["equity", "commodity", "crypto"].includes(node.type);
  if (tab === "flow") return ["fx", "rates"].includes(node.type);
  if (tab === "news") return signalIds.has(node.id);
  return true;
}

function marketNodeColor(node) {
  if (node.type === "hub") return typeColors.hub;
  if (!Number.isFinite(Number(node.changePct))) return "#8b97a8";
  return Number(node.changePct) >= 0 ? "#ff4d4f" : "#34d399";
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function popupHtml(node) {
  const color = marketNodeColor(node);
  return `
    <div class="leaflet-finance-popup">
      <div class="popup-title-row">
        <span style="background:${color}">${escapeHtml(node.symbol || node.id)}</span>
        <strong>${escapeHtml(node.label)}</strong>
      </div>
      <div class="popup-meta">${escapeHtml(typeLabels[node.type] || node.type)} · ${escapeHtml(node.region)}</div>
      <div class="popup-price">
        <strong>${escapeHtml(formatPrice(node))}</strong>
        <em class="${changeClass(node.changePct)}">${escapeHtml(formatChange(node.changePct))}</em>
      </div>
      <div class="popup-source">${escapeHtml(node.source || "public source")} · ${escapeHtml(formatTime(node.asOf))}</div>
    </div>`;
}

function eventToneClass(event) {
  if (event.type === "agent") return "agent";
  if (event.sentiment === "positive") return "positive";
  if (event.sentiment === "negative") return "negative";
  return "watch";
}

function eventPopupHtml(event) {
  return `
    <div class="leaflet-finance-popup intel-popup">
      <div class="popup-title-row">
        <span class="intel-popup-badge ${eventToneClass(event)}">${event.type === "agent" ? "AG" : "NEWS"}</span>
        <strong>${escapeHtml(event.title)}</strong>
      </div>
      <div class="popup-meta">${escapeHtml(event.source || event.agentName || "资讯")} · ${escapeHtml(event.relatedLabel || event.relatedNodeId || "Global")}</div>
      <p>${escapeHtml(event.summary || event.objective || event.mapSync || "")}</p>
      <div class="popup-source">${escapeHtml(formatTime(event.publishedAt || event.createdAt))}</div>
    </div>`;
}

function edgeColor(edge) {
  if (edge.relation === "contains") return "#6b7b91";
  if (edge.weight >= 1.7) return "#ff4d4f";
  if (edge.weight >= 1.3) return "#f59e0b";
  return "#22d3ee";
}

function GlobalMarketMap({ nodes, edges, newsEvents = [], agentEvents = [], selectedId, selectedEventId, onSelect, onSelectEvent, onReset }) {
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const markerLayerRef = useRef(null);
  const edgeLayerRef = useRef(null);
  const eventLayerRef = useRef(null);
  const markersRef = useRef(new Map());
  const eventMarkersRef = useRef(new Map());
  const [zoom, setZoom] = useState(2);
  const assetNodes = useMemo(() => nodes.filter((node) => node.type !== "hub" && Number.isFinite(node.lat) && Number.isFinite(node.lon)), [nodes]);
  const nodeById = useMemo(() => new Map(nodes.map((node) => [node.id, node])), [nodes]);
  const selectedNode = selectedId ? nodeById.get(selectedId) : null;
  const intelligenceEvents = useMemo(
    () => [...newsEvents, ...agentEvents].filter((event) => Number.isFinite(event.lat) && Number.isFinite(event.lon)),
    [newsEvents, agentEvents]
  );
  const selectedEvent = selectedEventId ? intelligenceEvents.find((event) => event.id === selectedEventId) : null;

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return undefined;

    const map = L.map(containerRef.current, {
      center: [18, 20],
      zoom: 2,
      minZoom: 2,
      maxZoom: 19,
      zoomControl: false,
      scrollWheelZoom: true,
      wheelDebounceTime: 18,
      wheelPxPerZoomLevel: 72,
      zoomSnap: 0.25,
      zoomDelta: 0.5,
      dragging: true,
      touchZoom: true,
      boxZoom: true,
      doubleClickZoom: true,
      worldCopyJump: true,
      inertia: true
    });

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      className: "finance-basemap",
      subdomains: "abcd",
      maxZoom: 20,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>'
    }).addTo(map);

    markerLayerRef.current = L.layerGroup().addTo(map);
    edgeLayerRef.current = L.layerGroup().addTo(map);
    eventLayerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;
    containerRef.current.__financeMap = map;
    map.fitBounds(WORLD_BOUNDS, { padding: [26, 26], animate: false });
    setZoom(map.getZoom());
    map.on("zoomend", () => setZoom(map.getZoom()));

    window.setTimeout(() => map.invalidateSize(), 80);

    return () => {
      if (containerRef.current) {
        delete containerRef.current.__financeMap;
      }
      map.remove();
      mapRef.current = null;
      markerLayerRef.current = null;
      edgeLayerRef.current = null;
      eventLayerRef.current = null;
      markersRef.current.clear();
      eventMarkersRef.current.clear();
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    const markerLayer = markerLayerRef.current;
    const edgeLayer = edgeLayerRef.current;
    const eventLayer = eventLayerRef.current;
    if (!map || !markerLayer || !edgeLayer || !eventLayer) return;

    markerLayer.clearLayers();
    edgeLayer.clearLayers();
    eventLayer.clearLayers();
    markersRef.current.clear();
    eventMarkersRef.current.clear();

    edges.forEach((edge) => {
      const source = nodeById.get(edge.source);
      const target = nodeById.get(edge.target);
      if (!source || !target || !Number.isFinite(source.lat) || !Number.isFinite(source.lon) || !Number.isFinite(target.lat) || !Number.isFinite(target.lon)) return;
      L.polyline(
        [
          [source.lat, source.lon],
          [target.lat, target.lon]
        ],
        {
          pane: "overlayPane",
          color: edgeColor(edge),
          weight: edge.relation === "contains" ? 0.55 : Math.min(1.25, 0.7 + edge.weight * 0.22),
          opacity: edge.relation === "contains" ? 0.16 : 0.34,
          dashArray: edge.relation === "contains" ? "2 7" : "3 9",
          lineCap: "round",
          interactive: false
        }
      ).addTo(edgeLayer);
    });

    assetNodes.forEach((node) => {
      const colorClass = changeClass(node.changePct);
      const signalClass = signalIds.has(node.id) ? " signal" : "";
      const marker = L.marker([node.lat, node.lon], {
        title: node.label,
        icon: L.divIcon({
          className: "leaflet-finance-marker-wrap",
          html: `<div class="leaflet-finance-marker ${colorClass}${signalClass}"><span>${escapeHtml(node.symbol || node.id)}</span></div>`,
          iconSize: [18, 18],
          iconAnchor: [9, 9]
        })
      });
      marker.bindPopup(popupHtml(node), { maxWidth: 280, className: "leaflet-finance-popup-shell" });
      marker.on("click", () => onSelect(node));
      marker.addTo(markerLayer);
      markersRef.current.set(node.id, marker);
    });

    intelligenceEvents.forEach((event) => {
      const marker = L.marker([event.lat, event.lon], {
        title: event.title,
        icon: L.divIcon({
          className: "leaflet-intel-marker-wrap",
          html: `<div class="leaflet-intel-marker ${eventToneClass(event)}"><span>${event.type === "agent" ? "A" : "N"}</span></div>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12]
        })
      });
      marker.bindPopup(eventPopupHtml(event), { maxWidth: 320, className: "leaflet-finance-popup-shell" });
      marker.on("click", () => onSelectEvent?.(event));
      marker.addTo(eventLayer);
      eventMarkersRef.current.set(event.id, marker);
    });
  }, [assetNodes, edges, intelligenceEvents, nodeById, onSelect, onSelectEvent]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedNode || !Number.isFinite(selectedNode.lat) || !Number.isFinite(selectedNode.lon)) return;
    const targetZoom = Math.max(map.getZoom(), selectedNode.type === "hub" ? 5 : 8);
    map.flyTo([selectedNode.lat, selectedNode.lon], targetZoom, { duration: 1.15, easeLinearity: 0.2 });
    const marker = markersRef.current.get(selectedNode.id);
    window.setTimeout(() => marker?.openPopup(), 450);
  }, [selectedNode]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !selectedEvent || !Number.isFinite(selectedEvent.lat) || !Number.isFinite(selectedEvent.lon)) return;
    map.flyTo([selectedEvent.lat, selectedEvent.lon], Math.max(map.getZoom(), selectedEvent.type === "agent" ? 6 : 7), { duration: 1.05, easeLinearity: 0.22 });
    const marker = eventMarkersRef.current.get(selectedEvent.id);
    window.setTimeout(() => marker?.openPopup(), 420);
  }, [selectedEvent]);

  const resetView = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    onReset();
    map.closePopup();
    map.fitBounds(WORLD_BOUNDS, { padding: [26, 26], animate: true, duration: 0.8 });
  }, [onReset]);

  return (
    <div className="map-stage leaflet-stage">
      <div ref={containerRef} className="leaflet-map" aria-label="可缩放拖拽的全球金融地图" />
      <div className="map-reset">
        <button type="button" onClick={resetView} disabled={!selectedId && zoom <= 2.05}>
          <RotateCcw size={15} />
          全球视图
        </button>
      </div>
      <div className="map-zoom-readout">Zoom {zoom.toFixed(1)}</div>
      {(selectedNode || selectedEvent) && (
        <div className="map-focus-badge">
          <LocateFixed size={15} />
          已聚焦 {selectedNode?.label || selectedEvent?.title}
        </div>
      )}
    </div>
  );
}

function ForceGraph({ nodes, edges }) {
  const option = useMemo(() => {
    const assetNodes = nodes.filter((node) => node.type !== "hub");
    return {
      backgroundColor: "transparent",
      animationDurationUpdate: 500,
      tooltip: {
        formatter: (params) => {
          if (params.dataType === "edge") return `${relationLabels[params.data.relation] || params.data.relation}<br/>${params.data.source} -> ${params.data.target}`;
          const item = params.data.raw;
          return `${item.label}<br/>${formatPrice(item)} / ${formatChange(item.changePct)}`;
        }
      },
      series: [
        {
          type: "graph",
          layout: "force",
          roam: true,
          draggable: true,
          top: 8,
          bottom: 8,
          left: 8,
          right: 8,
          force: { repulsion: 92, edgeLength: [42, 118], gravity: 0.08 },
          label: { show: true, position: "right", fontSize: 11, color: "#cbd5e1" },
          lineStyle: { color: "#6b7b91", width: 0.8, opacity: 0.34, curveness: 0.18 },
          data: assetNodes.map((node) => ({
            name: node.id,
            raw: node,
            value: node.changePct,
            symbolSize: 12 + Math.min(18, node.importance * 1.2 + Math.abs(node.changePct || 0) * 2),
            itemStyle: { color: typeColors[node.type] || "#64748b" },
            label: { formatter: node.label }
          })),
          links: edges.filter((item) => item.relation !== "contains").map((item) => ({ source: item.source, target: item.target, relation: item.relation, value: item.weight }))
        }
      ]
    };
  }, [nodes, edges]);
  const ref = useEChart(option, [option]);
  return <div ref={ref} className="graph-chart" />;
}

function NodeDetail({ node, edges, nodes }) {
  const byId = useMemo(() => new Map(nodes.map((item) => [item.id, item])), [nodes]);
  if (!node) {
    return (
      <section className="graph-panel detail-panel">
        <div className="panel-title">
          <Network size={18} />
          <h3>节点详情</h3>
        </div>
        <p className="muted-copy">点击左侧任一资产或地图节点，地图会自动放大到对应区域，并打开该节点的关系视图。</p>
      </section>
    );
  }

  const related = edges.filter((item) => item.source === node.id || item.target === node.id);
  return (
    <section className="graph-panel detail-panel">
      <div className="panel-title">
        <CircleDollarSign size={18} />
        <h3>{node.label}</h3>
      </div>
      <div className="detail-price">
        <strong>{formatPrice(node)}</strong>
        <span className={changeClass(node.changePct)}>{formatChange(node.changePct)}</span>
      </div>
      <dl className="detail-list">
        <div>
          <dt>类型</dt>
          <dd>{typeLabels[node.type] || node.type}</dd>
        </div>
        <div>
          <dt>区域</dt>
          <dd>{node.region}</dd>
        </div>
        <div>
          <dt>状态</dt>
          <dd>{node.marketState || "-"}</dd>
        </div>
        <div>
          <dt>来源</dt>
          <dd>{node.source}</dd>
        </div>
        <div>
          <dt>时间</dt>
          <dd>{formatTime(node.asOf)}</dd>
        </div>
      </dl>
      <div className="relation-list">
        {related.length ? (
          related.map((item, index) => {
            const peerId = item.source === node.id ? item.target : item.source;
            const peer = byId.get(peerId);
            return (
              <div key={`${item.source}-${item.target}-${index}`} className="relation-row">
                <span>{relationLabels[item.relation] || item.relation}</span>
                <strong>{peer?.label || peerId}</strong>
              </div>
            );
          })
        ) : (
          <p className="muted-copy">暂无关系边。</p>
        )}
      </div>
    </section>
  );
}

function SourcePanel({ sources, failures }) {
  return (
    <div className="source-panel">
      {sources.map((source) => (
        <div className="source-item" key={source.name}>
          <span className="source-dot green" />
          <span className="source-name">{source.name}</span>
          <span className="source-status">online</span>
        </div>
      ))}
      <div className="source-item">
        <span className={failures?.length ? "source-dot orange" : "source-dot green"} />
        <span className="source-name">免费源容错</span>
        <span className="source-status">{failures?.length || 0} fail</span>
      </div>
    </div>
  );
}

function NewsFeedPanel({ news, selectedEventId, onSelect }) {
  return (
    <section className="intel-panel">
      <div className="intel-panel-head">
        <span>
          <Newspaper size={15} />
          实时资讯雷达
        </span>
        <strong>{news.length}</strong>
      </div>
      <div className="intel-news-list">
        {news.slice(0, 10).map((item) => (
          <button key={item.id} type="button" className={selectedEventId === item.id ? "intel-news-row active" : "intel-news-row"} onClick={() => onSelect(item)}>
            <span className={`intel-dot ${eventToneClass(item)}`} />
            <strong>{item.title}</strong>
            <small>{item.source} · {item.relatedLabel} · {formatTime(item.publishedAt)}</small>
          </button>
        ))}
      </div>
    </section>
  );
}

function RadarHook({ locked, onToggle, newsCount, runCount }) {
  return (
    <section className={locked ? "radar-hook locked" : "radar-hook"}>
      <div className="radar-hook-title">
        <BellRing size={16} />
        <strong>每日 Agent 地图站会</strong>
      </div>
      <p>把隔夜新闻、资产异动和未完成 Agent 任务合成一张晨会地图；每天回来解锁新的链路。</p>
      <div className="radar-hook-stats">
        <span>{newsCount} 条资讯</span>
        <span>{runCount} 个协同任务</span>
        <span>{locked ? "已锁定" : "待锁定"}</span>
      </div>
      <button type="button" onClick={onToggle}>
        {locked ? <CheckCircle2 size={15} /> : <Target size={15} />}
        {locked ? "今日雷达已锁定" : "锁定我的每日雷达"}
      </button>
    </section>
  );
}

function AgentCommandCenter({ agents, connectors, selectedNode, selectedEvent, runs, selectedAgentId, onAgentChange, onRun }) {
  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) || agents[0];
  const activeConnectors = connectors.filter((connector) => selectedAgent?.connectors?.includes(connector.id));
  const anchor = selectedEvent?.relatedLabel || selectedNode?.label || "全球市场";

  return (
    <section className="graph-panel agent-command-panel">
      <div className="panel-title">
        <Bot size={18} />
        <h3>金融 Agent 协同台</h3>
      </div>
      <div className="agent-picker">
        {agents.map((agent) => (
          <button key={agent.id} type="button" className={selectedAgent?.id === agent.id ? "active" : ""} onClick={() => onAgentChange(agent.id)}>
            <span>{agent.name}</span>
            <small>{agent.group}</small>
          </button>
        ))}
      </div>
      {selectedAgent && (
        <div className="agent-playbook">
          <div>
            <small>当前锚点</small>
            <strong>{anchor}</strong>
          </div>
          <p>{selectedAgent.trigger}：{selectedAgent.mapHook}</p>
          <div className="agent-output-grid">
            {selectedAgent.produces.map((item) => (
              <span key={item}>
                <FileText size={13} />
                {item}
              </span>
            ))}
          </div>
          <button className="agent-run-button" type="button" onClick={() => onRun(selectedAgent)}>
            <PlayCircle size={16} />
            启动协同并同步地图
          </button>
        </div>
      )}
      <div className="connector-strip">
        <span>
          <Link2 size={14} />
          MCP Integrations
        </span>
        {activeConnectors.slice(0, 4).map((connector) => (
          <strong key={connector.id}>{connector.name}</strong>
        ))}
      </div>
      <div className="agent-run-list">
        {runs.slice(0, 5).map((run) => (
          <div key={run.id} className="agent-run-row">
            <span className={run.status === "running" ? "run-status running" : "run-status"} />
            <strong>{run.title}</strong>
            <small>{run.agentName} · {run.relatedLabel}</small>
          </div>
        ))}
      </div>
    </section>
  );
}

export function GlobalMarketGraph() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [assetFilter, setAssetFilter] = useState("all");
  const [regionFilter, setRegionFilter] = useState("global");
  const [activeTab, setActiveTab] = useState("all");
  const [selected, setSelected] = useState(null);
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [localAgentRuns, setLocalAgentRuns] = useState([]);
  const [selectedAgentId, setSelectedAgentId] = useState("market-researcher");
  const [radarLocked, setRadarLocked] = useState(false);

  const loadGraph = useCallback(async (force = false) => {
    force ? setRefreshing(true) : setLoading(true);
    setError("");
    try {
      const response = await fetch(`/api/global-market-graph${force ? "?refresh=1" : ""}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.error || "全球市场图谱加载失败");
      setData(payload);
      setSelected((current) => (current ? payload.nodes.find((node) => node.id === current.id) || current : null));
      setSelectedEvent((current) => (current ? [...(payload.news || []), ...(payload.agentRuns || []), ...localAgentRuns].find((item) => item.id === current.id) || current : null));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [localAgentRuns]);

  useEffect(() => {
    loadGraph(false);
    const timer = window.setInterval(() => loadGraph(false), 60_000);
    return () => window.clearInterval(timer);
  }, [loadGraph]);

  const visible = useMemo(() => {
    if (!data) return { nodes: [], edges: [], assets: [] };
    const assets = data.nodes.filter((node) => {
      if (node.type === "hub") return false;
      const typeOk = assetFilter === "all" || node.type === assetFilter;
      const regionOk = regionFilter === "global" || regionBucket(node) === regionFilter;
      return typeOk && regionOk && tabMatch(activeTab, node);
    });
    const assetIds = new Set(assets.map((node) => node.id));
    const hubIds = new Set(assets.map((node) => node.hub).filter(Boolean));
    const nodes = data.nodes.filter((node) => assetIds.has(node.id) || hubIds.has(node.id));
    const ids = new Set(nodes.map((node) => node.id));
    return { nodes, assets, edges: data.edges.filter((item) => ids.has(item.source) && ids.has(item.target)) };
  }, [data, assetFilter, regionFilter, activeTab]);

  const newsEvents = useMemo(() => data?.news || [], [data]);
  const starterAgentRuns = useMemo(() => data?.agentRuns || [], [data]);
  const agentEvents = useMemo(
    () => [...localAgentRuns, ...starterAgentRuns].map((run) => ({
      ...run,
      type: "agent",
      source: run.agentName,
      title: run.title,
      summary: run.objective || run.mapSync,
      publishedAt: run.createdAt || data?.generatedAt,
      sentiment: "agent",
      impact: 4
    })),
    [data?.generatedAt, localAgentRuns, starterAgentRuns]
  );
  const topMover = data?.pulse?.topMovers?.[0];
  const sortedAssets = [...visible.assets].sort((a, b) => Math.abs(b.changePct || 0) - Math.abs(a.changePct || 0));

  const selectNode = useCallback((node) => {
    setSelected(node);
    setSelectedEvent(null);
  }, []);

  const selectEvent = useCallback((event) => {
    setSelectedEvent(event);
    setSelected(null);
  }, []);

  const startAgentRun = useCallback((agent) => {
    if (!data || !agent) return;
    const anchorNode = selected || data.nodes.find((node) => node.id === selectedEvent?.relatedNodeId) || data.nodes.find((node) => node.id === "spx") || data.nodes.find((node) => node.type !== "hub");
    const createdAt = new Date().toISOString();
    const run = {
      id: `run-${agent.id}-${Date.now()}`,
      agentId: agent.id,
      agentName: agent.name,
      status: "running",
      title: `${agent.name} · ${anchorNode?.label || "全球市场"}`,
      objective: selectedEvent?.title ? `围绕资讯「${selectedEvent.title}」生成协同工作流。` : `围绕 ${anchorNode?.label || "全球市场"} 生成协同工作流。`,
      relatedNodeId: anchorNode?.id,
      relatedLabel: anchorNode?.label || "全球市场",
      lat: anchorNode?.lat ?? 20,
      lon: anchorNode?.lon ?? 0,
      outputs: agent.produces || [],
      mapSync: agent.mapHook,
      createdAt
    };
    setLocalAgentRuns((current) => [run, ...current].slice(0, 12));
    setSelectedEvent({ ...run, type: "agent", source: agent.name, summary: run.objective, publishedAt: createdAt, sentiment: "agent" });
  }, [data, selected, selectedEvent]);

  return (
    <main className="market-cockpit">
      <SiteTopNav />
      {error && <div className="graph-floating-error">{error}</div>}
      {loading && !data ? (
        <section className="loading-state cockpit-loading">
          <div className="loader" />
          <h2>正在拉取全球金融资讯……</h2>
        </section>
      ) : (
        data && (
          <div className="cockpit-shell">
            <aside className="cockpit-sidebar">
              <header className="cockpit-header">
                <p className="site-kicker">Global Financial Intelligence Graph</p>
                <h1>全球金融资讯图谱</h1>
                <p>把全球行情、新闻资讯、MCP 数据连接器和金融 Agent 协作结果放到同一张地图上，观察风险偏好与跨资产传导。</p>
              </header>

              <SourcePanel sources={data.sources || []} failures={data.failures || []} />

              <div className="graph-tabs">
                {Object.entries(tabLabels).map(([key, label]) => (
                  <button key={key} className={activeTab === key ? "active" : ""} type="button" onClick={() => setActiveTab(key)}>
                    {label}
                  </button>
                ))}
              </div>

              <div className="graph-select-grid">
                <label>
                  <span>资产类型</span>
                  <select value={assetFilter} onChange={(event) => setAssetFilter(event.target.value)}>
                    {Object.entries(typeLabels).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>区域</span>
                  <select value={regionFilter} onChange={(event) => setRegionFilter(event.target.value)}>
                    {Object.entries(regionLabels).map(([key, label]) => (
                      <option key={key} value={key}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              <button className="refresh-button cockpit-refresh" type="button" onClick={() => loadGraph(true)} disabled={refreshing || loading}>
                <RefreshCw size={17} className={refreshing ? "spinning" : ""} />
                {refreshing ? "刷新中" : "刷新实时数据源"}
              </button>

              <div className="signal-panel">
                <div className="signal-title">
                  <Satellite size={15} />
                  全球金融信息联动信号
                </div>
                <button type="button" onClick={() => selectNode(data.nodes.find((node) => node.id === "ust10y"))}>美债收益率影响成长股估值</button>
                <button type="button" onClick={() => selectNode(data.nodes.find((node) => node.id === "dxy"))}>美元强弱牵动商品和离岸风险资产</button>
                <button type="button" onClick={() => selectNode(data.nodes.find((node) => node.id === "btc"))}>BTC 与高波动风险资产情绪共振</button>
              </div>

              <NewsFeedPanel news={newsEvents} selectedEventId={selectedEvent?.id} onSelect={selectEvent} />

              <RadarHook locked={radarLocked} onToggle={() => setRadarLocked((value) => !value)} newsCount={newsEvents.length} runCount={agentEvents.length} />

              <div className="asset-list-head">
                <strong>全部资产</strong>
                <span>{visible.assets.length} 个节点</span>
              </div>
              <div className="market-node-list cockpit-node-list">
                {sortedAssets.map((node) => (
                  <button key={node.id} className={selected?.id === node.id ? "market-node-row active" : "market-node-row"} type="button" onClick={() => selectNode(node)}>
                    <span>
                      <strong>{node.label}</strong>
                      <small>{node.symbol || node.id} · {node.region}</small>
                    </span>
                    <em className={changeClass(node.changePct)}>{formatChange(node.changePct)}</em>
                  </button>
                ))}
              </div>
            </aside>

            <section className="cockpit-map-area">
              <div className="map-overlay stats-bar">
                <div className="stat-item">
                  <span>资讯事件</span>
                  <strong>{newsEvents.length}</strong>
                </div>
                <div className="stat-item">
                  <span>Agent 协同</span>
                  <strong>{agentEvents.length}</strong>
                </div>
                <div className="stat-item">
                  <span>市场状态</span>
                  <strong>{toneLabel(data.pulse?.tone)}</strong>
                </div>
                <div className="stat-item">
                  <span>最大波动</span>
                  <strong>{topMover ? `${topMover.label} ${formatChange(topMover.changePct)}` : "-"}</strong>
                </div>
              </div>

              <div className="map-overlay update-panel">
                <span className="source-dot green" />
                <span>最后刷新: <strong>{formatTime(data.generatedAt)}</strong></span>
              </div>

              <GlobalMarketMap
                nodes={visible.nodes}
                edges={visible.edges}
                newsEvents={newsEvents}
                agentEvents={agentEvents}
                selectedId={selected?.id}
                selectedEventId={selectedEvent?.id}
                onSelect={selectNode}
                onSelectEvent={selectEvent}
                onReset={() => {
                  setSelected(null);
                  setSelectedEvent(null);
                }}
              />
            </section>

            <aside className="cockpit-detail">
              <NodeDetail node={selected} nodes={data.nodes} edges={data.edges} />
              <AgentCommandCenter
                agents={data.agents || []}
                connectors={data.mcpIntegrations || []}
                selectedNode={selected}
                selectedEvent={selectedEvent}
                runs={agentEvents}
                selectedAgentId={selectedAgentId}
                onAgentChange={setSelectedAgentId}
                onRun={startAgentRun}
              />
              <section className="graph-panel">
                <div className="panel-title">
                  <Network size={18} />
                  <h3>关系力导图</h3>
                </div>
                <ForceGraph nodes={visible.nodes} edges={visible.edges} />
              </section>
              {data.failures?.length > 0 && (
                <section className="graph-warning">
                  <AlertCircle size={17} />
                  <span>{data.failures.length} 个免费数据源请求失败，页面已展示可用节点；刷新可重试。</span>
                </section>
              )}
              <section className="graph-panel compact-source-note">
                <div className="panel-title">
                  <DatabaseZap size={18} />
                  <h3>数据说明</h3>
                </div>
                <p>行情来自免费公开源，权益和期货可能存在交易所延迟；加密资产为 24/7 报价。</p>
              </section>
            </aside>
          </div>
        )
      )}
    </main>
  );
}
