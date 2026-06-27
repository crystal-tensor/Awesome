import { mkdir, writeFile } from "node:fs/promises";
import crypto from "node:crypto";
import path from "node:path";
import { XMLParser } from "fast-xml-parser";

const newsDir = path.resolve("news");

const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: "",
  textNodeName: "text"
});

const regions = [
  {
    id: "russia",
    label: "俄罗斯",
    scope: "Russia",
    defaultGeo: { label: "俄罗斯莫斯科", lat: 55.7558, lon: 37.6173 },
    relatedNodeId: "crude",
    relatedLabel: "WTI原油",
    region: "Europe",
    feeds: [
      { name: "Google News · Russia finance", url: googleNews("Russia financial markets OR ruble OR Moscow Exchange OR Russian central bank") },
      { name: "The Moscow Times", url: "https://www.themoscowtimes.com/rss/news", filter: /(ruble|rouble|market|bank|econom|oil|gas|sanction|finance|business|trade|stock|rate|inflation)/i }
    ]
  },
  {
    id: "canada",
    label: "加拿大",
    scope: "Canada",
    defaultGeo: { label: "加拿大多伦多", lat: 43.6532, lon: -79.3832 },
    relatedNodeId: "tsx",
    relatedLabel: "TSX",
    region: "Americas",
    feeds: [
      { name: "Bank of Canada · Press", url: "https://www.bankofcanada.ca/content_type/press/feed/" },
      { name: "Bank of Canada · News", url: "https://www.bankofcanada.ca/utility/news/feed/" },
      { name: "Google News · Canada finance", url: googleNews("Canada finance OR TSX OR Bank of Canada OR Canadian economy") }
    ]
  },
  {
    id: "south-america",
    label: "南美",
    scope: "South America",
    defaultGeo: { label: "巴西圣保罗", lat: -23.5505, lon: -46.6333 },
    relatedNodeId: "bovespa",
    relatedLabel: "Bovespa",
    region: "Americas",
    feeds: [
      { name: "Google News · South America finance", url: googleNews("South America finance OR Latam markets OR Brazil economy OR Argentina peso OR Chile copper") },
      { name: "Google News · Brazil markets", url: googleNews("Brazil financial markets OR Ibovespa OR Bovespa OR Petrobras OR Banco Central do Brasil") }
    ]
  },
  {
    id: "africa",
    label: "非洲",
    scope: "Africa",
    defaultGeo: { label: "南非约翰内斯堡", lat: -26.2041, lon: 28.0473 },
    relatedNodeId: "gold",
    relatedLabel: "黄金",
    region: "Commodities",
    feeds: [
      { name: "Google News · Africa finance", url: googleNews("Africa finance OR African markets OR AfDB OR South Africa rand OR Nigeria naira") },
      { name: "Google News · African economies", url: googleNews("African economy investment debt central bank markets") }
    ]
  },
  {
    id: "australia",
    label: "澳洲",
    scope: "Australia",
    defaultGeo: { label: "澳大利亚悉尼", lat: -33.8688, lon: 151.2093 },
    relatedNodeId: "asx",
    relatedLabel: "ASX 200",
    region: "Asia Pacific",
    feeds: [
      { name: "Reserve Bank of Australia · Media Releases", url: "https://www.rba.gov.au/rss/rss-cb-media-releases.xml" },
      { name: "Reserve Bank of Australia · Speeches", url: "https://www.rba.gov.au/rss/rss-cb-speeches.xml" },
      { name: "Google News · Australia finance", url: googleNews("Australia finance OR ASX OR RBA OR Australian economy OR iron ore") }
    ]
  }
];

const geos = [
  { label: "俄罗斯莫斯科", scope: "Russia", lat: 55.7558, lon: 37.6173, terms: ["moscow", "russia", "ruble", "rouble", "russian", "莫斯科", "俄罗斯", "卢布"] },
  { label: "加拿大多伦多", scope: "Canada", lat: 43.6532, lon: -79.3832, terms: ["tsx", "toronto", "canada", "canadian", "加拿大", "多伦多"] },
  { label: "加拿大渥太华", scope: "Canada", lat: 45.4215, lon: -75.6972, terms: ["bank of canada", "ottawa", "渥太华"] },
  { label: "巴西圣保罗", scope: "South America", lat: -23.5505, lon: -46.6333, terms: ["bovespa", "ibovespa", "sao paulo", "são paulo", "petrobras", "巴西", "圣保罗"] },
  { label: "巴西巴西利亚", scope: "South America", lat: -15.7939, lon: -47.8828, terms: ["banco central do brasil", "brasilia", "brasília", "巴西利亚"] },
  { label: "阿根廷布宜诺斯艾利斯", scope: "South America", lat: -34.6037, lon: -58.3816, terms: ["argentina", "buenos aires", "peso", "阿根廷"] },
  { label: "智利圣地亚哥", scope: "South America", lat: -33.4489, lon: -70.6693, terms: ["chile", "santiago", "copper", "智利", "铜"] },
  { label: "哥伦比亚波哥大", scope: "South America", lat: 4.711, lon: -74.0721, terms: ["colombia", "bogota", "bogotá", "哥伦比亚"] },
  { label: "南非约翰内斯堡", scope: "Africa", lat: -26.2041, lon: 28.0473, terms: ["south africa", "johannesburg", "rand", "南非", "约翰内斯堡"] },
  { label: "尼日利亚拉各斯", scope: "Africa", lat: 6.5244, lon: 3.3792, terms: ["nigeria", "lagos", "naira", "尼日利亚"] },
  { label: "肯尼亚内罗毕", scope: "Africa", lat: -1.2921, lon: 36.8219, terms: ["kenya", "nairobi", "肯尼亚"] },
  { label: "埃及开罗", scope: "Africa", lat: 30.0444, lon: 31.2357, terms: ["egypt", "cairo", "埃及"] },
  { label: "科特迪瓦阿比让", scope: "Africa", lat: 5.36, lon: -4.0083, terms: ["afdb", "african development bank", "abidjan", "非洲开发银行"] },
  { label: "澳大利亚悉尼", scope: "Australia", lat: -33.8688, lon: 151.2093, terms: ["asx", "sydney", "australia", "australian", "澳大利亚", "澳洲", "悉尼"] },
  { label: "澳大利亚堪培拉", scope: "Australia", lat: -35.2809, lon: 149.13, terms: ["rba", "reserve bank of australia", "canberra", "堪培拉"] },
  { label: "澳大利亚墨尔本", scope: "Australia", lat: -37.8136, lon: 144.9631, terms: ["melbourne", "墨尔本"] }
];

const categoryRules = [
  { id: "central-bank", terms: ["central bank", "reserve bank", "bank of canada", "rba", "rate", "inflation", "monetary", "policy"] },
  { id: "economic-data", terms: ["gdp", "cpi", "jobs", "employment", "pmi", "retail sales", "growth", "economy"] },
  { id: "commodities", terms: ["oil", "gas", "gold", "copper", "iron ore", "commodity", "mining", "energy"] },
  { id: "fx", terms: ["ruble", "rouble", "rand", "naira", "peso", "currency", "exchange rate", "dollar"] },
  { id: "geopolitics", terms: ["sanction", "war", "tariff", "conflict", "ukraine", "iran", "risk"] },
  { id: "rates", terms: ["bond", "yield", "treasury", "debt", "credit"] },
  { id: "finance", terms: ["market", "stock", "exchange", "bank", "finance", "investment", "tsx", "asx", "bovespa", "ibovespa"] }
];

function googleNews(query) {
  const encoded = encodeURIComponent(`${query} when:7d`);
  return `https://news.google.com/rss/search?q=${encoded}&hl=en-US&gl=US&ceid=US:en`;
}

function clean(value) {
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

function hash(value) {
  return crypto.createHash("sha1").update(value).digest("hex").slice(0, 14);
}

function absoluteUrl(url, base) {
  if (!url) return base;
  try {
    return new URL(url, base).toString();
  } catch {
    return base;
  }
}

function safeDate(value) {
  const parsed = new Date(value || Date.now());
  return Number.isNaN(parsed.getTime()) ? new Date().toISOString() : parsed.toISOString();
}

function asArray(value) {
  if (!value) return [];
  return Array.isArray(value) ? value : [value];
}

function itemLink(item, baseUrl) {
  if (typeof item.link === "string") return absoluteUrl(item.link, baseUrl);
  if (item.link?.href) return absoluteUrl(item.link.href, baseUrl);
  if (item.guid?.text) return absoluteUrl(item.guid.text, baseUrl);
  return baseUrl;
}

function geoFor(title, summary, region) {
  const haystack = `${title} ${summary}`.toLowerCase();
  return geos.find((geo) => geo.terms.some((term) => haystack.includes(term.toLowerCase()))) || {
    ...region.defaultGeo,
    scope: region.scope
  };
}

function categoryFor(title, summary) {
  const haystack = `${title} ${summary}`.toLowerCase();
  return categoryRules.find((rule) => rule.terms.some((term) => haystack.includes(term)))?.id || "finance";
}

function sentimentFor(title, summary) {
  const haystack = `${title} ${summary}`.toLowerCase();
  if (/(gain|rise|rises|rally|growth|beats|surge|upgrade|record|strong|improve|cut rates|eases)/i.test(haystack)) return "positive";
  if (/(fall|falls|drop|slump|risk|warning|default|sanction|war|inflation|weak|downgrade|crisis|loss)/i.test(haystack)) return "negative";
  return "watch";
}

function relatedFor(title, summary, region) {
  const haystack = `${title} ${summary}`.toLowerCase();
  if (/(oil|crude|gas|opec|energy)/i.test(haystack)) return { id: "crude", label: "WTI原油", region: "Commodities" };
  if (/(gold|bullion)/i.test(haystack)) return { id: "gold", label: "黄金", region: "Commodities" };
  if (/(copper|iron ore|mining|metal)/i.test(haystack)) return { id: "copper", label: "铜", region: "Commodities" };
  if (/(bond|yield|rate|central bank|reserve bank|bank of canada|rba)/i.test(haystack)) return { id: "ust10y", label: "美债10Y", region: "Rates" };
  if (/(currency|ruble|rouble|rand|naira|peso|dollar|exchange rate)/i.test(haystack)) return { id: "dxy", label: "美元指数", region: "FX" };
  return { id: region.relatedNodeId, label: region.relatedLabel, region: region.region };
}

async function fetchText(url) {
  const response = await fetch(url, {
    headers: { "user-agent": "Mozilla/5.0 FinancialIntelligenceLab/1.0" }
  });
  if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
  return response.text();
}

async function fetchFeed(feed, region) {
  const xml = await fetchText(feed.url);
  const parsed = parser.parse(xml);
  const items = asArray(parsed.rss?.channel?.item || parsed.feed?.entry);
  return items
    .map((item) => {
      const title = clean(item.title?.text || item.title);
      const summary = clean(item.description?.text || item.description || item.summary?.text || item.summary || item.content?.text || item.content || title).slice(0, 360);
      if (!title) return null;
      const haystack = `${title} ${summary}`;
      if (feed.filter && !feed.filter.test(haystack)) return null;
      const geo = geoFor(title, summary, region);
      const related = relatedFor(title, summary, region);
      const url = itemLink(item, feed.url);
      return {
        id: `regional-${region.id}-${hash(`${title}-${url}`)}`,
        type: "news",
        title,
        summary,
        category: categoryFor(title, summary),
        source: feed.name,
        url,
        publishedAt: safeDate(item.pubDate || item.updated || item.published || item["dc:date"]),
        relatedNodeId: related.id,
        relatedLabel: related.label,
        region: related.region,
        lat: geo.lat,
        lon: geo.lon,
        locationLabel: geo.label,
        geoScope: geo.scope,
        sentiment: sentimentFor(title, summary),
        impact: sentimentFor(title, summary) === "watch" ? 2 : 3,
        regionalBucket: region.label
      };
    })
    .filter(Boolean);
}

async function main() {
  const failures = [];
  const batches = await Promise.all(regions.flatMap((region) => (
    region.feeds.map(async (feed) => {
      try {
        return await fetchFeed(feed, region);
      } catch (error) {
        failures.push({ region: region.label, source: feed.name, url: feed.url, error: error.message });
        return [];
      }
    })
  )));

  const deduped = new Map();
  for (const item of batches.flat()) {
    const key = `${item.title.toLowerCase()}-${item.geoScope}`;
    if (!deduped.has(key)) deduped.set(key, item);
  }

  const items = [...deduped.values()]
    .sort((a, b) => new Date(b.publishedAt) - new Date(a.publishedAt))
    .slice(0, 140);

  const payload = {
    generatedAt: new Date().toISOString(),
    description: "Regional finance news snapshot covering Russia, South America, Canada, Africa, and Australia. Headlines and short summaries only; article bodies remain at source URLs.",
    regions: regions.map((region) => region.label),
    failures,
    items
  };

  await mkdir(newsDir, { recursive: true });
  const today = new Date().toISOString().slice(0, 10);
  await writeFile(path.join(newsDir, "regional-finance-latest.json"), JSON.stringify(payload, null, 2));
  await writeFile(path.join(newsDir, `regional-finance-archive-${today}.json`), JSON.stringify(payload, null, 2));
  console.log(JSON.stringify({
    generatedAt: payload.generatedAt,
    itemCount: items.length,
    byRegion: items.reduce((map, item) => {
      map[item.geoScope] = (map[item.geoScope] || 0) + 1;
      return map;
    }, {}),
    failures
  }, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
