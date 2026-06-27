import React from "react";
import { Bot, Database, GitBranch, Landmark, LineChart, Network, Shield, Users } from "lucide-react";
import { SiteTopNav } from "./portalHome.jsx";

const eras = [
  {
    badge: "第一代",
    years: "1970s - 1990s",
    title: "数据产品",
    color: "blue",
    desc: "核心逻辑是消除信息差。终端订阅把价格、新闻和数据分发速度变成商业壁垒。",
    examples: ["Bloomberg Terminal", "Reuters", "Wind", "东方财富"]
  },
  {
    badge: "第二代",
    years: "1980s - 2010s",
    title: "交易产品",
    color: "cyan",
    desc: "数据普及之后，竞争焦点变成超额收益能力、策略 IP、风控和执行基础设施。",
    examples: ["Renaissance", "Bridgewater", "Two Sigma", "Citadel"]
  },
  {
    badge: "第三代",
    years: "2009 - 至今",
    title: "共识产品",
    color: "violet",
    desc: "网络共识本身成为价值来源，区块链让信任、转让和规则执行可以被编程。",
    examples: ["Bitcoin", "Ethereum", "DeFi", "Stablecoin"]
  },
  {
    badge: "第四代",
    years: "2020 - 至今",
    title: "预测产品",
    color: "rose",
    desc: "概率被产品化、流动性化，市场共识成为对未来事件的实时价格发现机制。",
    examples: ["Polymarket", "Kalshi", "Augur", "Metaculus"]
  },
  {
    badge: "第五代",
    years: "2025 - ?",
    title: "智能体金融产品",
    color: "green",
    desc: "自主智能成为服务本身。用户不只是买工具，而是调用可审计、可反馈、可持续进化的金融研究 Agent。",
    examples: ["Agent PM", "Agent Marketplace", "A2A Economy", "Reputation Token"]
  }
];

const architecture = [
  { icon: Database, title: "数据感知层", desc: "行情、新闻、宏观、链上数据" },
  { icon: Bot, title: "多智能体决策核", desc: "研究、风控、回测、审计 Agent" },
  { icon: LineChart, title: "交付层", desc: "报告、图谱、情景矩阵、审计包" },
  { icon: Shield, title: "合规边界", desc: "不托管资金、不自动交易、不承诺收益" }
];

export function AgentEvolution() {
  return (
    <main className="site-shell evolution-page">
      <SiteTopNav />

      <section className="evolution-hero">
        <p className="site-kicker">Financial Product Evolution</p>
        <h1>金融产品的五代演进，与智能体金融的未来</h1>
        <p>
          从卖数据，到卖 Alpha，到卖共识，再到卖概率。第五代金融产品会把“自主研究、推理透明、结果验收”变成新的产品形态。
        </p>
      </section>

      <section className="timeline-panel">
        {eras.map((era) => (
          <article className={`era-node ${era.color}`} key={era.badge}>
            <div className="era-marker" />
            <div className="era-content">
              <div className="era-heading">
                <span>{era.badge}</span>
                <strong>{era.title}</strong>
                <em>{era.years}</em>
              </div>
              <p>{era.desc}</p>
              <div className="era-tags">
                {era.examples.map((item) => (
                  <span key={item}>{item}</span>
                ))}
              </div>
            </div>
          </article>
        ))}
      </section>

      <section className="portal-section">
        <div className="section-copy">
          <p className="site-kicker">Agent Finance Stack</p>
          <h2>智能体金融不是一个页面，而是一套运行机制</h2>
          <p>它把数据、推理、回测、图谱和审计放进同一个闭环，让金融研究从一次性输出变成持续进化的交付系统。</p>
        </div>
        <div className="architecture-grid">
          {architecture.map(({ icon: Icon, title, desc }) => (
            <article className="portal-card" key={title}>
              <div className="portal-card-icon">
                <Icon size={22} />
              </div>
              <h3>{title}</h3>
              <p>{desc}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="portal-split">
        <div>
          <p className="site-kicker">Why It Matters</p>
          <h2>产品从“工具”变成“可审计的研究主体”</h2>
        </div>
        <div className="principle-grid">
          <div className="principle-step">
            <Landmark size={18} />
            <span>金融约束</span>
          </div>
          <div className="principle-step">
            <Network size={18} />
            <span>跨资产图谱</span>
          </div>
          <div className="principle-step">
            <Users size={18} />
            <span>人类验收</span>
          </div>
          <div className="principle-step">
            <GitBranch size={18} />
            <span>持续进化</span>
          </div>
        </div>
      </section>
    </main>
  );
}
