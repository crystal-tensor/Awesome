#!/usr/bin/env python3
"""Run FinTerra's financial roundtable through MiroFish's installed LLM client.

The flow mirrors the successful QuanKnowledeg implementation:
seed roles -> agent personas -> round-by-round speeches -> round summaries ->
coordinator conclusion. The financial graph only seeds personas and evidence;
the answer is produced by repeated MiroFish LLM calls.
"""

import json
import os
import re
import sys
from pathlib import Path

import httpx


ROOT = Path(__file__).resolve().parents[1]
MIROFISH_BACKEND = ROOT / "vendor" / "MiroFish" / "backend"
if str(MIROFISH_BACKEND) not in sys.path:
    sys.path.insert(0, str(MIROFISH_BACKEND))


def extract_json_object(text):
    raw = (text or "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", raw)
        if not match:
            raise ValueError("MiroFish LLM did not return a JSON object")
        return json.loads(match.group(0))


def clip(text, limit=900):
    text = re.sub(r"\s+", " ", str(text or "")).strip()
    return text[:limit]


def normalize_base_url(url):
    base = (url or "https://api.deepseek.com/v1").rstrip("/")
    if base.endswith("/chat/completions"):
        base = base[: -len("/chat/completions")]
    if base == "https://api.deepseek.com":
        base = "https://api.deepseek.com/v1"
    return base


def openai_chat_url(base_url):
    base = normalize_base_url(base_url)
    if base.endswith("/chat/completions"):
        return base
    return f"{base}/chat/completions"


def chat(config, messages, temperature=0.55, max_tokens=1400, response_format=None):
    payload = {
        "model": config["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format:
        payload["response_format"] = response_format
    headers = {
        "Authorization": f"Bearer {config['api_key']}",
        "Content-Type": "application/json",
    }
    timeout = httpx.Timeout(connect=8.0, read=58.0, write=12.0, pool=8.0)
    with httpx.Client(timeout=timeout, trust_env=False) as client:
        response = client.post(openai_chat_url(config["base_url"]), headers=headers, json=payload)
    if response.status_code != 200:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"LLM API {response.status_code}: {str(detail)[:500]}")
    data = response.json()
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return (message.get("content") or message.get("reasoning_content") or "").strip()


def normalize_roundtable(parsed, seed_roles):
    roles = parsed.get("roles") or []
    if not roles:
        raise ValueError("MiroFish LLM did not generate agent roles")

    seed_by_id = {role.get("id"): role for role in seed_roles}
    normalized_roles = []
    for index, role in enumerate(roles):
        seed = seed_by_id.get(role.get("id")) or (seed_roles[index] if index < len(seed_roles) else {})
        normalized_roles.append(
            {
                "id": role.get("id") or seed.get("id") or f"agent-{index + 1}",
                "name": role.get("name") or seed.get("name") or f"FinTerra Agent {index + 1}",
                "stance": role.get("stance") or seed.get("stance") or "neutral",
                "goal": role.get("goal") or seed.get("stance") or "参与金融资讯推演",
                "role": role.get("role") or role.get("expertise") or "金融图谱智能体",
                "expertise": role.get("expertise") or "跨资产金融资讯分析",
                "persona": role.get("persona") or role.get("goal") or "",
                "evidenceTitles": seed.get("evidenceTitles") or [],
            }
        )

    role_ids = {role["id"] for role in normalized_roles}
    role_name_by_id = {role["id"]: role["name"] for role in normalized_roles}
    rounds = parsed.get("rounds") or []
    if len(rounds) != 3:
        raise ValueError("MiroFish LLM did not return exactly three discussion rounds")

    normalized_rounds = []
    for round_index, round_item in enumerate(rounds, start=1):
        turns = round_item.get("turns") or []
        if len(turns) < len(normalized_roles):
            raise ValueError(f"MiroFish LLM round {round_index} did not include every agent")
        normalized_turns = []
        seen = set()
        for turn in turns:
            role_id = turn.get("roleId") or turn.get("role_id") or turn.get("id")
            if role_id not in role_ids:
                name = turn.get("roleName") or turn.get("role_name") or turn.get("name")
                matched = next((role["id"] for role in normalized_roles if role["name"] == name), None)
                role_id = matched or normalized_roles[len(normalized_turns) % len(normalized_roles)]["id"]
            message = clip(turn.get("message") or turn.get("content") or turn.get("speech"), 520)
            if not message:
                raise ValueError(f"MiroFish LLM round {round_index} returned an empty agent speech")
            seen.add(role_id)
            normalized_turns.append(
                {
                    "roleId": role_id,
                    "roleName": role_name_by_id.get(role_id) or turn.get("roleName") or "FinTerra Agent",
                    "message": message,
                    "round": round_index,
                }
            )
        if len(seen) < len(normalized_roles):
            raise ValueError(f"MiroFish LLM round {round_index} missed one or more agents")
        summary = round_item.get("summary") or ""
        if not summary:
            raise ValueError(f"MiroFish LLM round {round_index} missed the round summary")
        if not summary.startswith(f"第{round_index}轮总结"):
            summary = f"第{round_index}轮总结：{summary}"
        normalized_rounds.append(
            {
                "round": round_index,
                "focus": round_item.get("focus") or ["证据读取与初始判断", "跨资产传导与角色交叉质询", "分歧收敛与情景判断"][round_index - 1],
                "turns": normalized_turns,
                "summary": clip(summary, 700),
            }
        )

    final = parsed.get("finalConclusion") or parsed.get("answer") or ""
    if not final:
        raise ValueError("MiroFish LLM did not return a final conclusion")
    return {
        "roles": normalized_roles,
        "rounds": normalized_rounds,
        "finalConclusion": final,
        "confidence": parsed.get("confidence") or "medium",
    }


def generate_complete_roundtable(client, question, graph):
    """Use one real LLM call to avoid long serial stalls while preserving turns."""
    seed_roles = (graph.get("seedRoles") or [])[:5]
    evidence = (graph.get("evidence") or [])[:18]
    prompt = {
        "task": "你正在作为 MiroFish 多智能体仿真引擎执行 FinTerra 金融推演。金融图谱只用于生成角色与证据，回答必须由多智能体讨论产出。",
        "question": question,
        "seedRoles": seed_roles,
        "evidence": evidence,
        "required_discussion_protocol": [
            "先根据 seedRoles 生成同等数量的 agents，不要少于 4 个；每个 agent 必须有 id、name、role、expertise、stance、goal、persona。",
            "必须进行 3 轮讨论。",
            "每一轮所有 agents 都必须轮流发言一次，turns 顺序与 roles 顺序一致。",
            "第1轮：各角色读取证据并提出初始判断。",
            "第2轮：角色交叉质询资产、区域、流动性和风险偏好传导。",
            "第3轮：角色收敛分歧，形成情景判断。",
            "每轮结束后必须输出 summary，且以“第n轮总结：”开头。",
            "最终输出 finalConclusion，直接回答用户问题，并给出关键传导路径和观察信号。",
        ],
        "output_schema": {
            "roles": [
                {
                    "id": "沿用 seedRoles.id",
                    "name": "中文角色名",
                    "role": "角色定位",
                    "expertise": "专业领域",
                    "stance": "角色立场",
                    "goal": "本轮推演目标",
                    "persona": "第一人称人设，不超过120字",
                }
            ],
            "rounds": [
                {
                    "round": 1,
                    "focus": "本轮主题",
                    "turns": [
                        {
                            "roleId": "对应 roles.id",
                            "roleName": "对应 roles.name",
                            "message": "第一人称发言，必须引用证据或区域/资产链路，80-160字",
                        }
                    ],
                    "summary": "第1轮总结：...",
                }
            ],
            "finalConclusion": "300-500字最终结论",
            "confidence": "low|medium|medium-high|high",
        },
        "rules": [
            "只输出 JSON，不要 markdown。",
            "不要说自己无法访问实时数据，证据已在输入中给出。",
            "不得输出投资建议或交易指令。",
        ],
    }
    raw = chat(
        client,
        [
            {"role": "system", "content": "你是 MiroFish LLMClient 的金融多智能体推演运行时。你必须输出严格 JSON。"},
            {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
        ],
        temperature=0.62,
        max_tokens=7000,
        response_format={"type": "json_object"},
    )
    parsed = extract_json_object(raw)
    return normalize_roundtable(parsed, seed_roles)


def build_agent_personas(client, question, graph):
    seed_roles = graph.get("seedRoles") or []
    evidence = graph.get("evidence") or []
    evidence_text = "\n".join(
        f"- [{item.get('id')}] {item.get('title')} | {item.get('locationLabel') or item.get('geoScope')} | {item.get('relatedLabel')} | {item.get('sentiment')}"
        for item in evidence[:16]
    )
    prompt = {
        "task": "根据 FinTerra 金融图谱种子角色生成多智能体 persona",
        "question": question,
        "seedRoles": seed_roles,
        "evidence": evidence[:16],
        "schema": {
            "roles": [
                {
                    "id": "必须沿用 seedRoles.id",
                    "name": "中文显示名",
                    "stance": "optimistic|neutral|pessimistic 或中文立场",
                    "goal": "本角色在推演中的目标",
                    "role": "角色定位",
                    "expertise": "专业领域",
                    "persona": "第一人称人设，不超过120字",
                }
            ]
        },
        "rules": [
            "不要新增和金融图谱无关的角色",
            "每个 seedRole 都必须保留",
            "只输出 JSON",
        ],
    }
    try:
        raw = chat(
            client,
            [
                {"role": "system", "content": "你是 MiroFish 的 agent persona 生成器，只输出 JSON。"},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            temperature=0.55,
            max_tokens=2200,
            response_format={"type": "json_object"},
        )
        parsed = extract_json_object(raw)
        roles = parsed.get("roles") or []
    except Exception:
        roles = []

    if not roles:
        roles = [
            {
                "id": role.get("id"),
                "name": role.get("name"),
                "stance": role.get("stance", "neutral"),
                "goal": role.get("stance", "从图谱证据出发参与金融推演"),
                "role": "金融图谱智能体",
                "expertise": "、".join((role.get("anchors") or {}).get("categories") or []) or "跨资产金融资讯分析",
                "persona": role.get("stance", "我代表该金融图谱视角参与讨论。"),
            }
            for role in seed_roles
        ]

    seed_by_id = {item.get("id"): item for item in seed_roles}
    normalized = []
    for role in roles:
        seed = seed_by_id.get(role.get("id")) or {}
        normalized.append(
            {
                "id": role.get("id") or seed.get("id"),
                "name": role.get("name") or seed.get("name") or "FinTerra Agent",
                "stance": role.get("stance") or seed.get("stance") or "neutral",
                "goal": role.get("goal") or seed.get("stance") or "参与金融资讯推演",
                "role": role.get("role") or "金融图谱智能体",
                "expertise": role.get("expertise") or "跨资产金融资讯分析",
                "persona": role.get("persona") or seed.get("stance") or "",
                "evidenceTitles": seed.get("evidenceTitles") or [],
            }
        )
    return normalized


def generate_agent_speech(client, agent, round_num, question, conversation_history, graph):
    evidence_text = "\n".join(
        f"- {item.get('title')} | {item.get('locationLabel') or item.get('geoScope')} | {item.get('relatedLabel')} | {item.get('sentiment')}"
        for item in (graph.get("evidence") or [])[:12]
    )
    prompt = f"""你是 {agent['name']}，{agent.get('role', '金融图谱智能体')}。

你的人设：
{agent.get('persona', '')}

你的专业领域：{agent.get('expertise', '')}
你的立场：{agent.get('stance', 'neutral')}
你的目标：{agent.get('goal', '')}

讨论问题：{question}

FinTerra 图谱证据：
{evidence_text}

至今为止的讨论记录：
{conversation_history or '（讨论刚开始，你是本轮发言者之一）'}

请以上面身份在第{round_num}轮发言。要求：
1. 必须回应当前问题，不能泛泛而谈
2. 必须引用至少一个图谱证据或地理/资产链路
3. 要回应前面角色的观点
4. 120-220字，用第一人称
5. 不要加角色名前缀，直接输出发言内容
"""
    return chat(client, [{"role": "user", "content": prompt}], temperature=0.72, max_tokens=900)


def generate_round_summary(client, round_num, question, round_speeches):
    speeches_text = "\n\n".join(f"{s['roleName']}：{s['message']}" for s in round_speeches)
    prompt = f"""请对第{round_num}轮金融多智能体讨论做总结。

讨论问题：{question}

本轮发言：
{speeches_text}

要求：
1. 必须以“第{round_num}轮总结：”开头
2. 总结核心观点、共识、分歧和下一轮需要追问的传导链
3. 120-200字
"""
    summary = chat(client, [{"role": "user", "content": prompt}], temperature=0.45, max_tokens=700)
    if not summary.startswith(f"第{round_num}轮总结"):
        summary = f"第{round_num}轮总结：{summary}"
    return summary


def generate_final_conclusion(client, question, roles, rounds):
    discussion = []
    for rnd in rounds:
        discussion.append(f"第{rnd['round']}轮主题：{rnd.get('focus')}")
        for turn in rnd.get("turns", []):
            discussion.append(f"{turn['roleName']}：{turn['message']}")
        discussion.append(rnd.get("summary", ""))
    prompt = f"""你是 MiroFish 多智能体推演协调者。请基于以下三轮金融讨论给出最终结论。

用户问题：{question}

参与角色：{', '.join(role['name'] for role in roles)}

讨论记录：
{chr(10).join(discussion)}

输出要求：
1. 直接回答问题
2. 明确关键传导路径：资讯/地区 -> 资产 -> 风险偏好/资金流
3. 给出需要继续观察的 3-5 个信号
4. 加入“非投资建议”的研究口径，但不要啰嗦
5. 300-500字
"""
    return chat(client, [{"role": "user", "content": prompt}], temperature=0.5, max_tokens=1500)


def run_roundtable(client, question, graph):
    return generate_complete_roundtable(client, question, graph)


def main():
    payload = json.loads(sys.stdin.read() or "{}")
    api_key = payload.get("apiKey")
    base_url = normalize_base_url(payload.get("baseUrl"))
    model = payload.get("model") or "deepseek-chat"
    question = payload.get("question") or ""
    graph = payload.get("graph") or {}

    if not api_key:
        raise ValueError("LLM_API_KEY is required")

    os.environ["LLM_API_KEY"] = api_key
    os.environ["LLM_BASE_URL"] = base_url
    os.environ["LLM_MODEL_NAME"] = model

    # We intentionally mirror QuanKnowledeg's working OpenAI-compatible
    # transport here: direct HTTP with trust_env=False. The surrounding
    # workflow remains MiroFish-style multi-agent simulation.
    client_config = {"api_key": api_key, "base_url": base_url, "model": model}
    result = run_roundtable(client_config, question, graph)
    print(json.dumps({"result": result, "raw": json.dumps(result, ensure_ascii=False)}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        sys.exit(0)
