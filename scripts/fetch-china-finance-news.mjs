import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const newsDir = path.resolve("news");

const sourceHome = {
  eastmoney: "https://kuaixun.eastmoney.com/",
  sina: "https://finance.sina.com.cn/",
  yicai: "https://www.yicai.com/",
  stcn: "https://www.stcn.com/",
  cs: "https://www.cs.com.cn/"
};

const assetAnchors = [
  { id: "hsi", label: "恒生指数", region: "China / HK", terms: ["港股", "香港", "恒生", "港交所", "赴港", "H股"] },
  { id: "usdcny", label: "USD/CNY", region: "FX", terms: ["人民币", "汇率", "离岸", "在岸", "外汇", "美元兑人民币"] },
  { id: "crude", label: "WTI原油", region: "Commodities", terms: ["原油", "石油", "油价", "霍尔木兹", "OPEC", "能源"] },
  { id: "gold", label: "黄金", region: "Commodities", terms: ["黄金", "金价", "贵金属"] },
  { id: "copper", label: "铜", region: "Commodities", terms: ["铜", "铝", "稀土", "有色", "金属", "锂", "MDI"] },
  { id: "nasdaq", label: "Nasdaq", region: "Americas", terms: ["AI", "人工智能", "算力", "半导体", "芯片", "英伟达", "美光", "特斯拉"] },
  { id: "ust10y", label: "美债10Y", region: "Rates", terms: ["债券", "国债", "收益率", "利率", "央行", "降息", "加息"] },
  { id: "shcomp", label: "上证指数", region: "China / HK", terms: ["A股", "沪指", "上交所", "深交所", "创业板", "科创板", "北交所", "券商", "IPO", "上市公司", "股份", "回购", "减持", "金融业", "中国市场"] }
];

const geoAnchors = [
  { label: "霍尔木兹海峡", scope: "Middle East", lat: 26.566, lon: 56.25, terms: ["霍尔木兹"] },
  { label: "伊朗", scope: "Middle East", lat: 35.6892, lon: 51.389, terms: ["伊朗", "德黑兰"] },
  { label: "以色列", scope: "Middle East", lat: 31.7683, lon: 35.2137, terms: ["以色列", "耶路撒冷"] },
  { label: "美国纽约", scope: "United States", lat: 40.7128, lon: -74.006, terms: ["美股", "纳斯达克", "标普", "道指", "华尔街", "纽约", "美国股市"] },
  { label: "美国加州", scope: "United States", lat: 37.7749, lon: -122.4194, terms: ["特斯拉", "苹果", "英伟达", "Alphabet", "Meta", "OpenAI", "硅谷", "加州"] },
  { label: "美国爱达荷州", scope: "United States", lat: 43.615, lon: -116.2023, terms: ["美光", "Micron"] },
  { label: "美国华盛顿", scope: "United States", lat: 38.9072, lon: -77.0369, terms: ["美联储", "白宫", "美国政府", "美国商务部", "美国财政部", "关税"] },
  { label: "中国北京", scope: "China", lat: 39.9042, lon: 116.4074, terms: ["国新办", "商务部", "人民银行", "央行", "证监会", "国务院", "北京", "政策措施", "监管"] },
  { label: "中国上海", scope: "China", lat: 31.2304, lon: 121.4737, terms: ["上交所", "沪指", "上海", "科创板", "A股", "中国市场", "外资机构", "金融业开放"] },
  { label: "中国深圳", scope: "China", lat: 22.5431, lon: 114.0579, terms: ["深交所", "创业板", "深圳", "比亚迪", "宁德时代"] },
  { label: "中国香港", scope: "Hong Kong", lat: 22.3193, lon: 114.1694, terms: ["香港", "港股", "港交所", "恒生", "赴港", "H股"] },
  { label: "日本东京", scope: "Japan", lat: 35.6762, lon: 139.6503, terms: ["日本", "东京", "日经"] },
  { label: "韩国首尔", scope: "South Korea", lat: 37.5665, lon: 126.978, terms: ["韩国", "首尔", "韩股"] },
  { label: "英国伦敦", scope: "United Kingdom", lat: 51.5072, lon: -0.1276, terms: ["英国", "英媒", "伦敦", "英国首相"] },
  { label: "德国法兰克福", scope: "Germany", lat: 50.1109, lon: 8.6821, terms: ["德国", "法兰克福", "欧洲央行"] },
  { label: "法国巴黎", scope: "France", lat: 48.8566, lon: 2.3522, terms: ["法国", "巴黎"] },
  { label: "欧盟布鲁塞尔", scope: "Eurozone", lat: 50.8503, lon: 4.3517, terms: ["欧盟", "欧元区", "欧洲"] },
  { label: "刚果（金）金沙萨", scope: "Africa", lat: -4.4419, lon: 15.2663, terms: ["刚果（金）", "刚果", "埃博拉"] }
];

const categoryRules = [
  { id: "technology", terms: ["AI", "人工智能", "算力", "半导体", "芯片", "机器人", "数据", "科技", "特斯拉", "商汤"] },
  { id: "central-bank", terms: ["央行", "人民银行", "货币政策", "降息", "加息", "金融业开放"] },
  { id: "economic-data", terms: ["GDP", "CPI", "PMI", "经济数据", "增长", "消费", "投资", "出口", "外资"] },
  { id: "rates", terms: ["债券", "国债", "收益率", "利率", "票据"] },
  { id: "fx", terms: ["人民币", "汇率", "外汇", "美元"] },
  { id: "commodities", terms: ["原油", "黄金", "铜", "铝", "稀土", "锂", "商品", "能源", "金属"] },
  { id: "geopolitics", terms: ["伊朗", "霍尔木兹", "关税", "制裁", "地缘", "谈判", "停火"] },
  { id: "earnings", terms: ["财报", "业绩", "利润", "营收", "预增", "预减"] },
  { id: "ipo-ma", terms: ["IPO", "并购", "收购", "重组", "上市"] },
  { id: "regulation", terms: ["监管", "合规", "证监会", "交易所", "市场监管"] },
  { id: "credit", terms: ["债务", "违约", "信用", "评级"] },
  { id: "real-estate", terms: ["地产", "房地产", "房贷", "住房"] },
  { id: "consumer", terms: ["消费", "零售", "端午", "票房", "白酒", "五粮液"] },
  { id: "energy", terms: ["能源", "电力", "石油", "天然气", "新能源"] },
  { id: "healthcare", terms: ["医疗", "医药", "药", "生物", "临床"] },
  { id: "risk", terms: ["风险", "下跌", "关闭", "停产", "检修", "减持", "承压"] },
  { id: "finance", terms: ["财经", "金融", "市场", "股票", "基金", "证券", "期货"] }
];

function text(value) {
  return String(value ?? "")
    .replace(/<script[\s\S]*?<\/script>/gi, " ")
    .replace(/<style[\s\S]*?<\/style>/gi, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}

function absoluteUrl(url, base) {
  if (!url) return base;
  try {
    return new URL(url, base).toString();
  } catch {
    return base;
  }
}

function isoFromChinaTime(value) {
  if (!value) return new Date().toISOString();
  if (/^\d+$/.test(String(value))) {
    const numeric = Number(value);
    return new Date((numeric > 10_000_000_000 ? numeric : numeric * 1000)).toISOString();
  }
  const normalized = String(value).replace(/\//g, "-").replace(" ", "T");
  const withZone = /Z|[+-]\d{2}:?\d{2}$/.test(normalized) ? normalized : `${normalized}+08:00`;
  const parsed = new Date(withZone);
  return Number.isNaN(parsed.getTime()) ? new Date().toISOString() : parsed.toISOString();
}

function classify(title, summary = "") {
  const haystack = `${title} ${summary}`;
  return categoryRules.find((rule) => rule.terms.some((term) => haystack.includes(term)))?.id || "other";
}

function anchor(title, summary = "") {
  const haystack = `${title} ${summary}`;
  return assetAnchors.find((rule) => rule.terms.some((term) => haystack.includes(term))) || assetAnchors.at(-1);
}

function geoAnchor(title, summary = "", source = "") {
  const haystack = `${title} ${summary}`;
  const matched = geoAnchors.find((rule) => rule.terms.some((term) => haystack.includes(term)));
  if (matched) return matched;
  if (/(外资|开放|市场|股票|股市|证券|基金|期货|券商|上市|IPO|并购|回购|减持|业绩|财报|消费|票房|航司|端午)/.test(haystack)) {
    return { label: "中国上海", scope: "China", lat: 31.2304, lon: 121.4737 };
  }
  if (/(政策|监管|发布会|通知|培训|税|金融|经济|数据|央行)/.test(haystack)) {
    return { label: "中国北京", scope: "China", lat: 39.9042, lon: 116.4074 };
  }
  if (source) return { label: "中国上海", scope: "China", lat: 31.2304, lon: 121.4737 };
  return { label: "全球", scope: "Global", lat: 20, lon: 0 };
}

function sentiment(title, summary = "") {
  const haystack = `${title} ${summary}`;
  if (/(上涨|涨超|走强|突破|受益|回购|获批|开放|吸引力|增长|机会|利好|升温)/.test(haystack)) return "positive";
  if (/(下跌|关闭|停产|风险|减持|承压|违约|调查|制裁|冲突|检修|收紧)/.test(haystack)) return "negative";
  return "watch";
}

function makeItem({ id, title, summary, source, url, publishedAt }) {
  const cleanTitle = text(title);
  const cleanSummary = text(summary || cleanTitle).slice(0, 260);
  const picked = anchor(cleanTitle, cleanSummary);
  const geo = geoAnchor(cleanTitle, cleanSummary, source);
  return {
    id,
    type: "news",
    title: cleanTitle,
    summary: cleanSummary,
    category: classify(cleanTitle, cleanSummary),
    source,
    url,
    publishedAt: isoFromChinaTime(publishedAt),
    relatedNodeId: picked.id,
    relatedLabel: picked.label,
    region: picked.region,
    lat: geo.lat,
    lon: geo.lon,
    locationLabel: geo.label,
    geoScope: geo.scope,
    sentiment: sentiment(cleanTitle, cleanSummary),
    impact: sentiment(cleanTitle, cleanSummary) === "watch" ? 2 : 3
  };
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { "user-agent": "Mozilla/5.0 FinancialIntelligenceLab/1.0" } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.json();
}

async function fetchText(url) {
  const response = await fetch(url, { headers: { "user-agent": "Mozilla/5.0 FinancialIntelligenceLab/1.0" } });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.text();
}

async function fromEastmoney() {
  const url = "https://np-listapi.eastmoney.com/comm/web/getFastNewsList?client=web&biz=web_724&fastColumn=102&sortEnd=&req_trace=1&pageSize=30&pageNo=1";
  const json = await fetchJson(url);
  return (json.data?.fastNewsList || []).map((item) => makeItem({
    id: `china-eastmoney-${item.code}`,
    title: item.title,
    summary: item.summary,
    source: "东方财富快讯",
    url: `https://kuaixun.eastmoney.com/a/${item.code}.html`,
    publishedAt: item.showTime
  }));
}

async function fromSina() {
  const url = "https://feed.mix.sina.com.cn/api/roll/get?pageid=155&lid=1686&num=30&page=1";
  const json = await fetchJson(url);
  return (json.result?.data || []).map((item) => makeItem({
    id: `china-sina-${item.docid || item.oid}`,
    title: item.title,
    summary: item.intro || item.summary || item.wapsummary,
    source: "新浪财经",
    url: item.url || item.wapurl || sourceHome.sina,
    publishedAt: item.ctime
  }));
}

async function fromYicai() {
  const url = "https://www.yicai.com/api/ajax/getjuhelist?action=news&page=1&pagesize=30";
  const json = await fetchJson(url);
  return json.map((item) => makeItem({
    id: `china-yicai-${item.NewsID}`,
    title: item.NewsTitle,
    summary: [item.ChannelName, item.NewsNotes, item.Tags].filter(Boolean).join(" · "),
    source: "第一财经",
    url: item.OuterUrl || item.ShareUrl || (item.NewsID ? `https://www.yicai.com/news/${item.NewsID}.html` : sourceHome.yicai),
    publishedAt: item.CreateDate || item.LastDate
  }));
}

async function fromStcn() {
  const json = await fetchJson("https://www.stcn.com/article/category-news-rank.html?type=kx");
  return (json.data || []).map((item) => makeItem({
    id: `china-stcn-${String(item.url || item.title).replace(/\D/g, "") || Buffer.from(item.title).toString("base64url").slice(0, 12)}`,
    title: item.title,
    summary: item.tag || item.title,
    source: "证券时报·人民财讯",
    url: absoluteUrl(item.url, sourceHome.stcn),
    publishedAt: new Date().toISOString()
  }));
}

async function fromCs() {
  const html = await fetchText(sourceHome.cs);
  const section = html.match(/<h3 class="ad_hna2">[\s\S]*?<ul style="display: none;">([\s\S]*?)<\/ul>/)?.[1] || html;
  const items = [];
  const pattern = /<li>\s*<em>([^<]+)<\/em>\s*<a href="([^"]+)"[^>]*title="([^"]+)"[^>]*>/g;
  for (const match of section.matchAll(pattern)) {
    const [, timePart, url, title] = match;
    items.push(makeItem({
      id: `china-cs-${Buffer.from(title).toString("base64url").slice(0, 16)}`,
      title,
      summary: `中证快讯 7x24 · ${timePart}`,
      source: "中证网",
      url,
      publishedAt: `${new Date().toISOString().slice(0, 10)} ${timePart}:00`
    }));
  }
  return items;
}

async function main() {
  const collectors = [
    ["东方财富快讯", fromEastmoney],
    ["新浪财经", fromSina],
    ["第一财经", fromYicai],
    ["证券时报·人民财讯", fromStcn],
    ["中证网", fromCs]
  ];
  const failures = [];
  const batches = await Promise.all(collectors.map(async ([name, fn]) => {
    try {
      return await fn();
    } catch (error) {
      failures.push({ source: name, error: error.message });
      return [];
    }
  }));

  const deduped = new Map();
  for (const item of batches.flat()) {
    if (!item.title || !item.url) continue;
    const key = `${item.title}-${item.source}`;
    if (!deduped.has(key)) deduped.set(key, item);
  }
  const items = [...deduped.values()]
    .sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt))
    .slice(0, 110);
  const payload = {
    generatedAt: new Date().toISOString(),
    description: "Chinese professional finance news snapshot. Headlines and short summaries only; article bodies remain at source URLs.",
    sources: collectors.map(([name]) => name),
    failures,
    items
  };

  await mkdir(newsDir, { recursive: true });
  const today = new Date().toISOString().slice(0, 10);
  await writeFile(path.join(newsDir, "china-finance-latest.json"), JSON.stringify(payload, null, 2));
  await writeFile(path.join(newsDir, `china-finance-archive-${today}.json`), JSON.stringify(payload, null, 2));
  console.log(JSON.stringify({
    generatedAt: payload.generatedAt,
    itemCount: items.length,
    sources: payload.sources,
    failures
  }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
