import React from "react";
import { ArrowRight, CheckCircle2, FileSearch, Globe2, ShieldCheck, TrendingUp } from "lucide-react";

const navItems = [
  ["全球图谱", "financial_intelligence_lab.html"],
  ["策略工作台", "strategy.html"],
  ["五代演进", "agent_finance_evolution.html"],
  ["API价格", "/model-api/"]
];

const products = [
  {
    icon: FileSearch,
    title: "研究智能体",
    desc: "把宏观事件、市场价格和证据链组织成可验收的研究交付物。",
    meta: "报告 · 证据 · 风险提示"
  },
  {
    icon: TrendingUp,
    title: "策略智能体",
    desc: "把策略假设落到历史数据、参数、回撤和压力情景里验证。",
    meta: "回测 · 参数 · 情景矩阵"
  },
  {
    icon: Globe2,
    title: "全球图谱智能体",
    desc: "把股票、外汇、利率、商品和加密资产放进同一张全球关系图。",
    meta: "地图 · 节点 · 跨资产传导"
  },
  {
    icon: ShieldCheck,
    title: "审计智能体",
    desc: "记录数据源、运行时间、结果状态和人工验收动作。",
    meta: "留痕 · 来源 · 版本"
  }
];

const agentLines = [
  ["09:30:01", "Research", "解析任务：美元利率上行对黄金、纳指、BTC 的路径影响"],
  ["09:30:06", "Market", "拉取 DXY、US10Y、GC=F、Nasdaq、BTC 的最新节点"],
  ["09:30:14", "Risk", "发现利率与风险资产同涨，标记为需要复核的异常组合"],
  ["09:30:26", "Audit", "生成来源、时间戳和验收状态，等待用户接受交付物"]
];

function SiteNav() {
  return (
    <nav className="site-nav">
      <a className="site-logo" href="index.html">
        <img src="/logo-wavefunction.png" alt="" />
        <span>FinTerra</span>
      </a>
      <div className="site-nav-links">
        {navItems.map(([label, href]) => (
          <a key={href} href={href}>
            {label}
          </a>
        ))}
      </div>
    </nav>
  );
}

export function PortalHome() {
  return (
    <main className="site-shell">
      <SiteNav />

      <section className="portal-hero">
        <div className="portal-hero-copy">
          <p className="site-kicker">Financial Agent Research Platform</p>
          <h1>不卖用量，卖可验证的金融研究交付物</h1>
          <p>
            FinTerra 把全球市场数据、策略回测和多智能体研究流程收束到一个工作台里。它不是投资顾问，不托管资金，不自动交易，只帮助你把问题变成可审计、可复核、可接受的结果。
          </p>
          <div className="site-actions">
            <a className="site-primary" href="financial_intelligence_lab.html">
              进入全球图谱
              <ArrowRight size={17} />
            </a>
            <a className="site-secondary" href="strategy.html">
              打开策略工作台
            </a>
          </div>
        </div>

        <section className="terminal-preview" aria-label="智能体运行预览">
          <div className="terminal-head">
            <span />
            <span />
            <span />
            <strong>fc2049-agent-runner</strong>
          </div>
          <div className="terminal-body">
            {agentLines.map(([time, agent, text]) => (
              <div className="terminal-line" key={`${time}-${agent}`}>
                <time>{time}</time>
                <strong>{agent}</strong>
                <span>{text}</span>
              </div>
            ))}
          </div>
          <div className="acceptance-strip">
            <CheckCircle2 size={16} />
            草稿免费，用户接受交付物后才进入计费与审计。
          </div>
        </section>
      </section>

      <section className="portal-section">
        <div className="section-copy">
          <p className="site-kicker">Product Matrix</p>
          <h2>一套视觉语言，四个金融智能体入口</h2>
          <p>门户负责叙事，图谱负责实时态势，策略页负责验证，演进页负责解释智能体金融为什么会成为新范式。</p>
        </div>
        <div className="portal-product-grid">
          {products.map(({ icon: Icon, title, desc, meta }) => (
            <article className="portal-card" key={title}>
              <div className="portal-card-icon">
                <Icon size={22} />
              </div>
              <h3>{title}</h3>
              <p>{desc}</p>
              <span>{meta}</span>
            </article>
          ))}
        </div>
      </section>

      <section className="portal-split">
        <div>
          <p className="site-kicker">Operating Principle</p>
          <h2>从“用了多少”转向“交付是否被接受”</h2>
        </div>
        <div className="principle-grid">
          {["生成研究草稿", "校验数据来源", "用户复核验收", "记录审计轨迹"].map((item, index) => (
            <div className="principle-step" key={item}>
              <strong>{String(index + 1).padStart(2, "0")}</strong>
              <span>{item}</span>
            </div>
          ))}
        </div>
      </section>

      <footer className="site-footer">
        <span>Research tool only. Not investment advice. No custody. No automatic trading.</span>
        <a href="mailto:wavefunction61@gmail.com">wavefunction61@gmail.com</a>
      </footer>
    </main>
  );
}

export function SiteTopNav() {
  return <SiteNav />;
}
