import React from "react";
import { ArrowRight, CheckCircle2, Clock3, Code2, DatabaseZap, KeyRound, LockKeyhole, ServerCog, ShieldCheck, Zap } from "lucide-react";
import { SiteTopNav } from "./portalHome.jsx";

const endpoints = [
  ["POST", "/v1/signals/rank", "返回指定市场的模型排序与风险标签"],
  ["POST", "/v1/market/minute", "读取分钟级行情并生成实时特征"],
  ["POST", "/v1/market/tick", "读取更细粒度 tick 数据能力"],
  ["POST", "/v1/model/infer", "提交标的池，返回模型推理结果"]
];

const plans = [
  {
    name: "展示版",
    price: "免费",
    cadence: "公开网站访问",
    desc: "只能查看页面效果、样例图谱和延迟展示结果。",
    features: ["无需 API Key", "不提供模型参数", "不开放最新分钟或 tick 数据", "不承诺实时可用性"]
  },
  {
    name: "API Basic",
    price: "¥299",
    cadence: "/ 月",
    desc: "适合个人研究和低频自动化调用。",
    features: ["10,000 次/月", "年付 8 折：¥2,870/年", "日线与小时级数据", "标准模型推理接口", "邮件技术支持"]
  },
  {
    name: "API Pro",
    price: "¥1,299",
    cadence: "/ 月",
    desc: "适合需要随时调用模型和分钟数据的团队。",
    features: ["200,000 次/月", "年付 8 折：¥12,470/年", "分钟级数据接口", "批量标的池推理", "优先队列与调用审计"]
  },
  {
    name: "Enterprise",
    price: "定制",
    cadence: "私有协议",
    desc: "适合机构部署、专线接入和更细 tick 数据需求。",
    features: ["独立额度与限速", "tick 数据接入", "私有网络白名单", "SLA 与合规留痕"]
  }
];

const boundaries = [
  {
    icon: LockKeyhole,
    title: "展示站不暴露模型",
    text: "公开网页只展示效果与历史样例，不下发模型参数、权重、实时特征或可复用的最新数据。"
  },
  {
    icon: ServerCog,
    title: "模型服务独立部署",
    text: "模型运行在伦敦节点，应用与 API 网关在新加坡承接访问、鉴权、限速和审计。"
  },
  {
    icon: DatabaseZap,
    title: "实时数据只走 API",
    text: "分钟图、更细 tick 数据和最新推理结果需要付费 Key，按套餐获得不同粒度和调用额度。"
  }
];

function CodeBlock() {
  return (
    <pre className="api-code-block">
      <code>{`curl https://api.finterra.ai/v1/model/infer \\
  -H "Authorization: Bearer ft_live_xxx" \\
  -H "Content-Type: application/json" \\
  -d '{
    "market": "US",
    "symbols": ["AAPL", "NVDA", "TSLA"],
    "interval": "1m",
    "features": ["rank", "risk", "regime"]
  }'`}</code>
    </pre>
  );
}

export function ModelApiPage() {
  return (
    <main className="site-shell api-page">
      <SiteTopNav />

      <section className="api-hero">
        <div className="api-hero-copy">
          <p className="site-kicker">Model API Pricing</p>
          <h1>付费 API 才能调用模型和实时数据</h1>
          <p>
            展示网站负责让用户看到效果；付费 API 负责随时随地调用伦敦模型服务，并按权限访问最新数据、分钟图和更细粒度 tick 数据。
          </p>
        </div>

        <aside className="api-status-panel" aria-label="API 部署状态">
          <div className="terminal-head">
            <span />
            <span />
            <span />
            <strong>finterra-api-gateway</strong>
          </div>
          <div className="api-status-body">
            <div>
              <Clock3 size={18} />
              <span>App Region</span>
              <strong>Singapore</strong>
            </div>
            <div>
              <Zap size={18} />
              <span>Model Region</span>
              <strong>London</strong>
            </div>
            <div>
              <ShieldCheck size={18} />
              <span>Access</span>
              <strong>Paid Key Only</strong>
            </div>
          </div>
        </aside>
      </section>

      <section className="api-section api-doc-layout">
        <div>
          <p className="site-kicker">How To Call</p>
          <h2>三步接入 API</h2>
          <div className="api-step-list">
            <article>
              <KeyRound size={20} />
              <h3>1. 购买套餐并获取 Key</h3>
              <p>每个 Key 绑定套餐、额度、市场权限和数据粒度。</p>
            </article>
            <article>
              <Code2 size={20} />
              <h3>2. 请求模型接口</h3>
              <p>通过 HTTPS POST 传入市场、标的池、周期和需要返回的字段。</p>
            </article>
            <article>
              <CheckCircle2 size={20} />
              <h3>3. 记录审计结果</h3>
              <p>每次调用都会生成时间戳、额度消耗、数据粒度和响应状态。</p>
            </article>
          </div>
        </div>
        <CodeBlock />
      </section>

      <section className="api-section">
        <div className="section-copy">
          <p className="site-kicker">Plans</p>
          <h2>收费标准</h2>
          <p>公开页面免费，但不会提供模型参数或最新实时数据。需要稳定调用模型时，使用付费 API Key。</p>
        </div>
        <div className="api-pricing-grid">
          {plans.map((plan) => (
            <article className="api-price-card" key={plan.name}>
              <div className="api-price-head">
                <h3>{plan.name}</h3>
                <div>
                  <strong>{plan.price}</strong>
                  <span>{plan.cadence}</span>
                </div>
              </div>
              <p>{plan.desc}</p>
              <ul>
                {plan.features.map((feature) => (
                  <li key={feature}>
                    <CheckCircle2 size={15} />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </article>
          ))}
        </div>
      </section>

      <section className="api-section api-boundary-grid">
        {boundaries.map(({ icon: Icon, title, text }) => (
          <article className="api-boundary-card" key={title}>
            <Icon size={22} />
            <h3>{title}</h3>
            <p>{text}</p>
          </article>
        ))}
      </section>

      <section className="api-section api-endpoints">
        <div>
          <p className="site-kicker">Endpoints</p>
          <h2>接口目录</h2>
        </div>
        <div className="api-endpoint-list">
          {endpoints.map(([method, path, desc]) => (
            <div className="api-endpoint-row" key={path}>
              <span>{method}</span>
              <code>{path}</code>
              <p>{desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="api-cta">
        <div>
          <p className="site-kicker">Start</p>
          <h2>申请付费 API Key</h2>
          <p>发送使用场景、需要的市场、数据粒度和预计调用量，我们会按套餐开通权限。</p>
        </div>
        <a className="site-primary" href="mailto:wavefunction61@gmail.com?subject=FinTerra%20API%20Key">
          联系开通
          <ArrowRight size={17} />
        </a>
      </section>

      <footer className="site-footer">
        <span>Free website shows results only. Model parameters and live data require paid API access.</span>
        <a href="mailto:wavefunction61@gmail.com">wavefunction61@gmail.com</a>
      </footer>
    </main>
  );
}
