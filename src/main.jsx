import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import * as echarts from "echarts";
import { BarChart3, CandlestickChart, ChevronRight, Play, Search, X } from "lucide-react";
import "./styles.css";

function todayAsYYYYMMDD() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}${month}${day}`;
}

const defaultRange = {
  start: "20220101",
  end: todayAsYYYYMMDD()
};

function percent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return `${(Number(value) * 100).toFixed(2)}%`;
}

function number(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(2);
}

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

function KlinePanel({ dates, data }) {
  const option = useMemo(() => {
    if (!dates || !data) return null;
    const { kline, ma5, ma20, buyPoints, sellPoints } = data;
    const buyData = buyPoints.map((item) => [item.date, item.price]);
    const sellData = sellPoints.map((item) => [item.date, item.price]);

    return {
      animation: false,
      tooltip: { trigger: "axis", axisPointer: { type: "cross" } },
      legend: { top: 8, data: ["K线", "MA5", "MA20", "买入", "卖出"] },
      grid: { left: 54, right: 32, top: 48, bottom: 42 },
      xAxis: { type: "category", data: dates, boundaryGap: true, axisLine: { lineStyle: { color: "#94a3b8" } } },
      yAxis: { scale: true, splitLine: { lineStyle: { color: "#e2e8f0" } } },
      dataZoom: [
        { type: "inside", start: 50, end: 100 },
        { type: "slider", height: 18, bottom: 8, start: 50, end: 100 }
      ],
      series: [
        {
          name: "K线",
          type: "candlestick",
          data: kline,
          itemStyle: {
            color: "#ef4444",
            color0: "#10b981",
            borderColor: "#ef4444",
            borderColor0: "#10b981"
          }
        },
        { name: "MA5", type: "line", data: ma5, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: "#f59e0b" } },
        { name: "MA20", type: "line", data: ma20, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: "#2563eb" } },
        {
          name: "买入",
          type: "scatter",
          data: buyData,
          symbol: "triangle",
          symbolSize: 14,
          itemStyle: { color: "#dc2626" },
          z: 5
        },
        {
          name: "卖出",
          type: "scatter",
          data: sellData,
          symbol: "triangle",
          symbolRotate: 180,
          symbolSize: 14,
          itemStyle: { color: "#059669" },
          z: 5
        }
      ]
    };
  }, [dates, data]);

  const ref = useEChart(option, [option]);
  return <div ref={ref} className="chart chart-tall" />;
}

function ReturnPanel({ result }) {
  const option = useMemo(() => {
    if (!result) return null;
    const { dates, netUniform, netPt } = result.series;
    return {
      animation: false,
      tooltip: { trigger: "axis" },
      legend: { top: 8, data: ["5-20均线策略", "量子5-20均线策略"] },
      grid: { left: 54, right: 28, top: 48, bottom: 34 },
      xAxis: { type: "category", data: dates, axisLine: { lineStyle: { color: "#94a3b8" } } },
      yAxis: { type: "value", scale: true, splitLine: { lineStyle: { color: "#e2e8f0" } } },
      dataZoom: [{ type: "inside", start: 50, end: 100 }],
      series: [
        { name: "5-20均线策略", type: "line", data: netUniform, showSymbol: false, lineStyle: { width: 2, color: "#2563eb" } },
        { name: "量子5-20均线策略", type: "line", data: netPt, showSymbol: false, lineStyle: { width: 2, color: "#e11d48" } }
      ]
    };
  }, [result]);

  const ref = useEChart(option, [option]);
  return <div ref={ref} className="chart chart-medium" />;
}

function StockModal({ market, onClose, onSelect }) {
  const [query, setQuery] = useState("");
  const customSymbol = query.trim().toUpperCase();
  const stocks = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return market.stocks;
    return market.stocks.filter((stock) => `${stock.symbol} ${stock.name}`.toLowerCase().includes(q));
  }, [market, query]);

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal" aria-modal="true">
        <div className="modal-head">
          <div>
            <p className="eyebrow">{market.region}</p>
            <h2>{market.name}</h2>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="关闭">
            <X size={18} />
          </button>
        </div>
        <label className="search-box">
          <Search size={18} />
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索代码或名称" />
        </label>
        <div className="stock-grid">
          {customSymbol && !stocks.some((stock) => stock.symbol.toUpperCase() === customSymbol) && (
            <button className="stock-row custom-stock" type="button" onClick={() => onSelect({ symbol: customSymbol, name: customSymbol })}>
              <span>使用代码</span>
              <strong>{customSymbol}</strong>
            </button>
          )}
          {stocks.map((stock) => (
            <button key={stock.symbol} className="stock-row" type="button" onClick={() => onSelect(stock)}>
              <span>{stock.name}</span>
              <strong>{stock.symbol}</strong>
            </button>
          ))}
        </div>
      </section>
    </div>
  );
}

function Metrics({ title, metrics, accent }) {
  const items = [
    ["夏普比率", number(metrics?.["夏普比率"])],
    ["累计收益率", percent(metrics?.["累计收益率"])],
    ["年化收益率", percent(metrics?.["年化收益率"])],
    ["最大回撤", percent(metrics?.["最大回撤"])]
  ];

  return (
    <section className="metric-group">
      <div className="metric-title" style={{ "--accent": accent }}>
        <span />
        {title}
      </div>
      <div className="metrics">
        {items.map(([label, value]) => (
          <div className="metric" key={label}>
            <small>{label}</small>
            <strong>{value}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function TradesTable({ trades }) {
  // 检查是否包含“量子算法买入价”这一列，来决定显示哪些表头
  const isPT = trades.length > 0 && "量子算法买入价" in trades[0];

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>买入日期</th>
            <th>卖出日期</th>
            {isPT && <th>量子算法买入价</th>}
            {isPT && <th>量子算法卖出价</th>}
            <th>真实买入价</th>
            <th>真实卖出价</th>
            <th>绝对收益</th>
            <th>收益率</th>
          </tr>
        </thead>
        <tbody>
          {trades.length ? (
            trades.map((trade, index) => (
              <tr key={`${trade["买入日期"]}-${index}`}>
                <td>{trade["买入日期"]}</td>
                <td>{trade["卖出日期"]}</td>
                {isPT && <td>{number(trade["量子算法买入价"])}</td>}
                {isPT && <td>{number(trade["量子算法卖出价"])}</td>}
                <td>{number(trade["买入价"])}</td>
                <td>{number(trade["卖出价"])}</td>
                <td className={trade["绝对收益"] >= 0 ? "up" : "down"}>{number(trade["绝对收益"])}</td>
                <td className={trade["收益率"] >= 0 ? "up" : "down"}>{percent(trade["收益率"])}</td>
              </tr>
            ))
          ) : (
            <tr>
              <td colSpan={isPT ? 8 : 6}>区间内无完整交易</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

function App() {
  const [markets, setMarkets] = useState([]);
  const [activeMarket, setActiveMarket] = useState(null);
  const [selected, setSelected] = useState(null);
  const [range, setRange] = useState(defaultRange);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/markets")
      .then((response) => response.json())
      .then((data) => {
        setMarkets(data.markets);
        const firstMarket = data.markets[0];
        setSelected(firstMarket?.stocks[0] || null);
      })
      .catch((err) => setError(err.message));
  }, []);

  const runBacktest = async () => {
    if (!selected) return;
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/backtest", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: selected.symbol, name: selected.name, start: range.start, end: range.end })
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || "回测失败");
      }
      setResult(data.result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="workspace">
      <aside className="sidebar">
        <div className="brand">
          <BarChart3 size={22} />
          <div>
            <h1>市场数据</h1>
          </div>
        </div>

        <nav className="market-list">
          {markets.map((market) => (
            <button key={market.id} className="market-button" type="button" onClick={() => setActiveMarket(market)}>
              <span>
                <strong>{market.name}</strong>
                <small>{market.region}</small>
              </span>
              <ChevronRight size={18} />
            </button>
          ))}
        </nav>

        <section className="run-panel">
          <p className="eyebrow">Selected</p>
          <h2>{selected?.name || "-"}</h2>
          <code>{selected?.symbol || "-"}</code>
          <div className="date-grid">
            <label>
              <span>开始</span>
              <input value={range.start} onChange={(event) => setRange({ ...range, start: event.target.value })} />
            </label>
            <label>
              <span>结束</span>
              <input value={range.end} onChange={(event) => setRange({ ...range, end: event.target.value })} />
            </label>
          </div>
          <button className="run-button" type="button" disabled={!selected || loading} onClick={runBacktest}>
            <Play size={18} fill="currentColor" />
            {loading ? "运行中" : "运行"}
          </button>
          
          <div className="disclaimer" style={{ marginTop: "24px", padding: "16px", backgroundColor: "#f8fafc", borderRadius: "8px", fontSize: "12px", color: "#64748b", lineHeight: "1.6" }}>
            <strong style={{ color: "#475569", display: "block", marginBottom: "8px" }}>重要声明：</strong>
            <ul style={{ margin: 0, paddingLeft: "16px" }}>
              <li>量子算法是研究工具，不是自动荐股工具</li>
              <li>不预测价格，不承诺收益，不保证风险控制</li>
              <li>所有回测结果仅供参考，不代表未来表现</li>
              <li>回测使用真实数据和量子算法计算的历史数据</li>
              <li>实盘前请自行验证策略并评估风险</li>
            </ul>
            <div style={{ marginTop: "12px", borderTop: "1px solid #e2e8f0", paddingTop: "12px" }}>
              联系方式：e-mail：<a href="mailto:wavefunction61@gmail.com" style={{ color: "#2563eb", textDecoration: "none" }}>wavefunction61@gmail.com</a>
            </div>
          </div>
        </section>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Backtest Workspace</p>
            <h2>{result ? `${result.stock.name} (${result.stock.yahooSymbol})` : "等待运行回测"}</h2>
          </div>
          {result && (
            <div className="range-chip">
              {result.dateRange.start} 至 {result.dateRange.end}
              <span>{result.dateRange.rows} 行</span>
            </div>
          )}
        </header>

        {error && <div className="error-banner">{error}</div>}

        {!result && !loading && (
          <section className="empty-state">
            <CandlestickChart size={44} />
            <h2>选择市场和股票后运行回测</h2>
          </section>
        )}

        {loading && (
          <section className="loading-state">
            <div className="loader" />
            <h2>正在运行 stock1.py</h2>
          </section>
        )}

        {result && (
          <>
            <div className="metric-layout">
              <Metrics title="5-20均线回测" metrics={result.metrics.uniform} accent="#2563eb" />
              <Metrics title="量子5-20均线回测" metrics={result.metrics.pt} accent="#e11d48" />
            </div>

            <section className="chart-section">
              <div className="section-head">
                <h3>真实历史 K 线与5-20均线买卖点</h3>
              </div>
              <KlinePanel dates={result.series.dates} data={result.series.uniform} />
            </section>

            <section className="chart-section">
              <div className="section-head">
                <h3>真实历史 K 线量子5-20均线与买卖点</h3>
              </div>
              <KlinePanel dates={result.series.dates} data={result.series.pt} />
            </section>

            <section className="chart-section">
              <div className="section-head">
                <h3>量子5-20均线算法与5-20均线收益率曲线</h3>
              </div>
              <ReturnPanel result={result} />
            </section>

            <section className="table-section">
              <div className="section-head">
                <h3>真实每次交易细节</h3>
              </div>
              <TradesTable trades={result.trades.uniform} />
            </section>

            <section className="table-section">
              <div className="section-head">
                <h3>量子算法每次交易细节</h3>
              </div>
              <TradesTable trades={result.trades.pt} />
            </section>
          </>
        )}
      </section>

      {activeMarket && (
        <StockModal
          market={activeMarket}
          onClose={() => setActiveMarket(null)}
          onSelect={(stock) => {
            setSelected(stock);
            setActiveMarket(null);
          }}
        />
      )}
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
