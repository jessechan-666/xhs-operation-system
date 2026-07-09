#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每天生成 keywords.json，并按需要轻量更新 templates.json。

安全说明（重要）：
- 为规避小红书账号违规风险，本脚本已**完全禁用**任何真实接口/千帆接口请求。
- 不会读取或使用 XHS_AUTHORIZATION / XHS_COOKIE 发起网络请求。
- keywords.json 数据全部使用本地规则（fallback）逻辑生成。

保留能力：
- 仍会维护 history.json / templates.json 的更新逻辑。

（兼容字段保留）
- 代码中仍可能保留部分旧的解析/请求函数，但已做“硬禁用”，不会在主流程中被调用。
"""

from __future__ import annotations

import json
import os
import re
import sys
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
# 注意：为规避风控风险，已禁用任何网络请求能力（不再导入 urllib.request）。

ROOT = Path(__file__).resolve().parent
KEYWORDS_PATH = ROOT / "keywords.json"
TEMPLATES_PATH = ROOT / "templates.json"
HISTORY_PATH = ROOT / "history.json"
TZ = timezone(timedelta(hours=8))

# 真实接口地址（已禁用，保留字段仅用于兼容历史代码）
API_URL = ""
DEFAULT_TIMEOUT = 20
API_PAGE_SIZE = 20

BASE_KEYWORDS = {
    "earring": [
        "耳夹合集 无耳洞女生必入",
        "显脸小耳饰推荐",
        "夏天戴什么耳环好看",
        "平价耳钉合集 学生党",
        "珍珠耳环 温柔气质",
        "通勤百搭耳饰",
        "不夹耳的耳夹推荐",
        "水晶耳钉 轻奢感",
        "显白耳饰颜色推荐",
        "小众设计感耳环",
        "高级感耳饰推荐",
        "约会耳饰怎么选",
        "无痛耳夹推荐",
        "通勤耳钉推荐",
    ],
    "ring": [
        "叠戴戒指搭配教程",
        "平价开口戒推荐",
        "显手白戒指合集",
        "情侣对戒 百元内",
        "复古戒指 ins风",
        "食指戒 时髦穿搭",
        "银戒指日常百搭",
        "珍珠戒指 优雅风",
        "宝石戒指 轻奢感",
        "可调节戒指不挑手型",
        "小众高级戒指",
        "显瘦手型戒指",
    ],
    "necklace": [
        "锁骨链推荐 显瘦",
        "叠戴项链 时髦穿搭",
        "珍珠项链 温柔气质",
        "平价项链合集",
        "钛钢项链 不过敏",
        "吊坠项链 送女友",
        "显脖子长的项链",
        "夏天必备锁骨链",
        "小众设计项链",
        "金色项链 百搭通勤",
        "轻奢项链推荐",
        "通勤锁骨链",
    ],
}

BASE_ACTIVITIES = [
    {"icon": "🎋", "name": "七夕情人节", "desc": "浪漫饰品送礼季", "color": "#FFE4EC"},
    {"icon": "🎓", "name": "开学季", "desc": "学生党平价饰品", "color": "#E8F5E9"},
    {"icon": "🌸", "name": "春日穿搭季", "desc": "换季焕新搭配", "color": "#FFF3E0"},
    {"icon": "💝", "name": "闺蜜节", "desc": "友情饰品推荐", "color": "#F3E5F5"},
    {"icon": "🎄", "name": "圣诞新年", "desc": "节日氛围饰品", "color": "#E3F2FD"},
    {"icon": "👩‍💼", "name": "职场新人季", "desc": "通勤轻熟风首饰", "color": "#ECEFF1"},
    {"icon": "🎁", "name": "生日礼物季", "desc": "送礼精选推荐", "color": "#FCE4EC"},
    {"icon": "☀️", "name": "夏日清凉感", "desc": "清透材质饰品", "color": "#E0F7FA"},
]

SEASONAL_BOOST = {
    1: ["新年饰品推荐", "红色耳饰", "年会配饰"],
    2: ["情人节礼物耳饰", "约会耳环", "玫瑰金耳饰"],
    3: ["春日耳饰", "花朵耳夹", "樱花配饰"],
    4: ["春夏耳饰", "清透耳饰", "减龄耳钉"],
    5: ["毕业礼物饰品", "初夏锁骨链", "通勤首饰"],
    6: ["夏日清凉感", "海边耳饰", "显白耳饰"],
    7: ["暑假出游耳饰", "七夕礼物预热", "清透珍珠耳饰"],
    8: ["七夕礼物", "约会耳饰", "送女生礼物饰品"],
    9: ["开学季耳饰", "学生党耳钉", "初秋饰品"],
    10: ["秋冬耳饰", "毛衣项链搭配", "氛围感耳环"],
    11: ["双11饰品好物", "囤货耳饰", "平价饰品清单"],
    12: ["圣诞耳饰", "年末礼物", "跨年配饰"],
}

HEAT_POOL = ["12.8w", "10.6w", "9.8w", "8.9w", "8.1w", "7.6w", "6.9w", "5.8w", "4.7w", "3.9w"]

ANALYSIS_CATEGORIES = ["earring", "ring", "necklace"]
ANALYSIS_CATEGORY_LABELS = {
    "earring": "耳饰",
    "ring": "戒指",
    "necklace": "项链",
}
HOT_SEARCH_LIMIT = 10
BLUE_OCEAN_LIMIT = 10
RISING_LIMIT = 10
LONG_TAIL_LIMIT = 10
VIRAL_NOTE_MIN_LIKES = 300
VIRAL_NOTE_MAX_FOLLOWERS = 2000
NOTE_DIRECTIONS = ["痛点场景", "穿搭种草", "送礼/情感"]

CATEGORY_HINT_ENV = {
    "earring": "XHS_EARRING_CATEGORY_ID",
    "ring": "XHS_RING_CATEGORY_ID",
    "necklace": "XHS_NECKLACE_CATEGORY_ID",
}

CATEGORY_KEYWORDS = {
    "earring": ["耳饰", "耳环", "耳钉", "耳夹", "耳坠", "耳骨夹", "耳圈", "耳", "珍珠耳环"],
    "ring": ["戒指", "对戒", "开口戒", "食指戒", "尾戒", "婚戒", "素圈", "戒"],
    "necklace": ["项链", "锁骨链", "吊坠", "颈链", "毛衣链", "链条", "珍珠项链"],
}

TEXT_KEYS = [
    "keywordName",
    "keyword",
    "keywordText",
    "query",
    "queryWord",
    "word",
    "text",
    "title",
    "name",
    "content",
]

HEAT_KEYS = [
    "heatText",
    "heat",
    "hotValueText",
    "hotValue",
    "hotScore",
    "score",
    "trendValue",
]


def now_cn() -> datetime:
    return datetime.now(TZ)


def stderr(msg: str) -> None:
    print(msg, file=sys.stderr)


def month_activities(dt: datetime) -> list[dict]:
    month = dt.month
    dynamic = []
    if month in (7, 8):
        dynamic.append({"icon": "💕", "name": "七夕预热期", "desc": "送礼/告白内容热度上升", "color": "#FDE7F3"})
    if month == 9:
        dynamic.append({"icon": "📚", "name": "开学焕新季", "desc": "学生党饰品内容高热", "color": "#E8F5E9"})
    if month in (11, 12):
        dynamic.append({"icon": "🛍️", "name": "年末送礼季", "desc": "礼盒、送礼、囤货笔记走高", "color": "#FFF3E0"})
    if month in (3, 4):
        dynamic.append({"icon": "🌷", "name": "春日出游季", "desc": "花朵、水晶、彩色配饰热度走高", "color": "#FFF0F5"})
    return dynamic + BASE_ACTIVITIES[:7]


def build_category_words(category: str, dt: datetime) -> list[dict]:
    base = list(dict.fromkeys(BASE_KEYWORDS[category]))
    seasonal = SEASONAL_BOOST.get(dt.month, [])
    merged = []
    for w in seasonal + base:
        if category == "earring" and any(k in w for k in ["耳", "耳夹", "耳钉", "耳环"]):
            merged.append(w)
        elif category == "ring" and any(k in w for k in ["戒", "对戒"]):
            merged.append(w)
        elif category == "necklace" and any(k in w for k in ["项链", "锁骨链", "吊坠"]):
            merged.append(w)
    if len(merged) < HOT_SEARCH_LIMIT:
        merged.extend(base)
    unique = []
    for item in merged:
        if item not in unique:
            unique.append(item)
    top_words = unique[:HOT_SEARCH_LIMIT]
    return [
        {
            "text": text,
            "heat": HEAT_POOL[i],
            "trend": f"↑{max(3.0, 18 - i * 1.3):.2f}%",
            "score": max(10000, (len(top_words) - i) * 10000),
            "ratio": max(0.03, 0.18 - i * 0.013),
        }
        for i, text in enumerate(top_words)
    ]


def build_hot_search_fallback(dt: datetime) -> dict:
    return {category: build_category_words(category, dt) for category in ANALYSIS_CATEGORIES}


def load_templates() -> dict:
    if TEMPLATES_PATH.exists():
        return json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))
    return {
        "updated_at": now_cn().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "v2.1",
        "directions": [],
        "title_formulas": {},
        "hook_sentences": {},
        "body_templates": {},
        "tag_templates": {},
    }


def refresh_templates(templates: dict, dt: datetime) -> dict:
    data = deepcopy(templates)
    data["updated_at"] = dt.strftime("%Y-%m-%d %H:%M:%S")

    month_tag = f"m{dt.month:02d}"
    old_version = str(data.get("version", "v2.1"))
    if month_tag not in old_version:
        data["version"] = f"{old_version}-{month_tag}"

    title_formulas = data.setdefault("title_formulas", {})
    visual_titles = title_formulas.setdefault("visual", [])
    seasonal_title = {
        7: "暑假氛围感拉满！{shortName}太出片",
        8: "七夕送这个！{shortName}氛围感绝了",
        9: "开学戴这个！{shortName}显脸小又百搭",
        12: "圣诞约会戴它！{shortName}太加分",
    }.get(dt.month)
    if seasonal_title and seasonal_title not in visual_titles:
        visual_titles.insert(0, seasonal_title)

    return data


def write_json(path: Path, data: dict | list) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_history() -> list[dict]:
    if not HISTORY_PATH.exists():
        return []
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def update_history(dt: datetime, keywords: dict) -> list[dict]:
    today = dt.strftime("%Y-%m-%d")
    entry = {
        "date": today,
        "updated_at": keywords["updated_at"],
        "recommended": keywords.get("recommended", []),
        "hot_search": keywords["hot_search"],
        "blue_ocean": keywords.get("blue_ocean", []),
        "rising": keywords.get("rising", []),
        "long_tail": keywords.get("long_tail", []),
        "activities": keywords["activities"],
    }

    history = [item for item in load_history() if item.get("date") != today]
    history.append(entry)
    history.sort(key=lambda item: item.get("date", ""), reverse=True)
    return history[:90]


def build_request_payload(first_category_id: str = "", query_group: int = 5) -> dict[str, Any]:
    return {
        "pageSource": 5,
        "firstCategoryId": first_category_id,
        "secondCategoryIdList": [],
        "onlyRelatedItemOwn": False,
        "queryGroup": query_group,
        "pageNo": 1,
        "pageSize": API_PAGE_SIZE,
        "sortOrders": [],
    }


def normalize_authorization(raw: str) -> str:
    value = raw.strip()
    if not value:
        return ""
    return value if value.lower().startswith("bearer ") else f"Bearer {value}"


def build_request_headers(include_signature: bool) -> dict[str, str]:
    """历史遗留：真实接口请求 headers 构造。

    已出于风控原因禁用，不再读取任何 XHS_* 环境变量，也不会生成 cookie/authorization。
    """

    raise RuntimeError("[xhs] 网络请求已禁用：build_request_headers 不可用")


def http_post_json(url: str, payload: dict[str, Any], headers: dict[str, str]) -> dict[str, Any]:
    """历史遗留：真实接口 POST 请求。

    已出于风控原因禁用。任何调用都会直接失败，以避免误触发带 cookie 的请求。
    """

    raise RuntimeError("[xhs] 网络请求已禁用：http_post_json 不可用")


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value).strip())


def format_heat(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return ""
    if numeric <= 0:
        return "0.00w+"
    return f"{numeric / 10000:.2f}w+"


def format_trend(value: Any) -> str:
    try:
        ratio = float(value)
    except (TypeError, ValueError):
        return "持平"
    percent = abs(ratio) * 100
    if percent < 1:
        return "持平"
    arrow = "↑" if ratio > 0 else "↓"
    return f"{arrow}{percent:.2f}%"


def build_keyword_entry(item: dict[str, Any]) -> dict[str, Any] | None:
    text = clean_text(item.get("keyword"))
    if not text:
        return None
    score = item.get("searchQv7dIndex")
    ratio = item.get("searchQv7dRatio")
    return {
        "text": text,
        "heat": format_heat(score),
        "trend": format_trend(ratio),
        "score": float(score or 0),
        "ratio": float(ratio or 0),
    }


def parse_keyword_list_response(response: dict[str, Any], request_name: str) -> list[dict[str, Any]]:
    code = response.get("code") if isinstance(response, dict) else None
    success = bool(response.get("success")) or code in (0, 200, "0", "200") if isinstance(response, dict) else False
    if not success:
        message = ""
        if isinstance(response, dict):
            message = str(response.get("msg") or response.get("message") or response.get("errorMsg") or "")
        raise RuntimeError(f"{request_name}: 接口返回为空或失败 code={code} msg={message}")

    data = response.get("data") if isinstance(response, dict) else None
    data_list = data.get("dataList") if isinstance(data, dict) else None
    if not isinstance(data_list, list):
        raise RuntimeError(f"{request_name}: 响应中缺少 data.dataList")

    normalized = []
    seen = set()
    for item in data_list:
        if not isinstance(item, dict):
            continue
        entry = build_keyword_entry(item)
        if not entry:
            continue
        key = entry["text"].lower()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(entry)

    if not normalized:
        raise RuntimeError(f"{request_name}: 接口成功但 data.dataList[].keyword 为空")

    stderr(f"[xhs] {request_name}: 获取到 {len(normalized)} 条关键词。")
    return normalized


def fetch_keyword_candidates(payload: dict[str, Any], include_signature: bool, request_name: str) -> list[dict[str, Any]]:
    """历史遗留：真实接口抓取入口（已禁用）。"""

    raise RuntimeError("[xhs] 网络请求已禁用：fetch_keyword_candidates 不可用")


def fetch_with_best_effort(payload: dict[str, Any], request_name: str) -> list[dict[str, Any]]:
    """历史遗留：真实接口重试逻辑（已禁用）。"""

    raise RuntimeError("[xhs] 网络请求已禁用：fetch_with_best_effort 不可用")


def strip_keyword_fields(item: dict[str, Any], include_trend: bool = True) -> dict[str, str]:
    result = {
        "text": item["text"],
        "heat": item["heat"],
    }
    if include_trend:
        result["trend"] = item["trend"]
    return result


def score_text_for_category(text: str, category: str) -> int:
    score = 0
    lowered = text.lower()
    for keyword in CATEGORY_KEYWORDS[category]:
        if keyword.lower() in lowered:
            score += max(2, len(keyword))
    if category == "earring" and "戒" in text:
        score -= 3
    if category == "ring" and any(token in text for token in ["项链", "锁骨链", "吊坠", "耳环", "耳饰"]):
        score -= 3
    if category == "necklace" and any(token in text for token in ["戒指", "对戒", "耳环", "耳饰", "耳钉"]):
        score -= 3
    return score


def append_fallback_items(selected: list[dict[str, Any]], category: str, dt: datetime, limit: int) -> list[dict[str, Any]]:
    if len(selected) >= limit:
        return selected[:limit]
    fallback = build_category_words(category, dt)
    existing = {item["text"] for item in selected}
    for item in fallback:
        if item["text"] in existing:
            continue
        selected.append(item)
        existing.add(item["text"])
        if len(selected) >= limit:
            break
    return selected[:limit]


def assign_keywords_from_generic_pool(pool: list[dict[str, Any]], dt: datetime) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {}
    for category in ANALYSIS_CATEGORIES:
        ranked = sorted(pool, key=lambda item: score_text_for_category(item["text"], category), reverse=True)
        selected: list[dict[str, Any]] = []
        seen = set()
        for item in ranked:
            if score_text_for_category(item["text"], category) <= 0:
                continue
            if item["text"] in seen:
                continue
            selected.append(item)
            seen.add(item["text"])
            if len(selected) >= HOT_SEARCH_LIMIT:
                break

        selected = append_fallback_items(selected, category, dt, HOT_SEARCH_LIMIT)

        if len(selected) < HOT_SEARCH_LIMIT:
            for item in pool:
                if item["text"] in seen:
                    continue
                selected.append(item)
                seen.add(item["text"])
                if len(selected) >= HOT_SEARCH_LIMIT:
                    break

        result[category] = [strip_keyword_fields(item) for item in selected[:HOT_SEARCH_LIMIT]]
    return result


def keywords_signature(items: list[dict[str, Any]]) -> tuple[str, ...]:
    return tuple(item["text"] for item in items)


def pick_recommended_from_pool(pool: list[dict[str, Any]], limit: int = HOT_SEARCH_LIMIT) -> list[dict[str, str]]:
    ranked = sorted(pool, key=lambda item: (item["score"], item["ratio"]), reverse=True)
    return [strip_keyword_fields(item) for item in ranked[:limit]]


def pick_blue_ocean_from_pool(pool: list[dict[str, Any]]) -> list[dict[str, str]]:
    ranked = sorted(pool, key=lambda item: (item["score"], -item["ratio"] or 0, len(item["text"])))
    return [strip_keyword_fields(item) for item in ranked[:BLUE_OCEAN_LIMIT]]


def pick_rising_from_pool(pool: list[dict[str, Any]]) -> list[dict[str, str]]:
    ranked = sorted(pool, key=lambda item: (item["ratio"], item["score"]), reverse=True)
    return [strip_keyword_fields(item) for item in ranked[:RISING_LIMIT]]


def pick_long_tail_from_hot_search(hot_search: dict[str, list[dict[str, str]]]) -> list[dict[str, str]]:
    merged = []
    seen = set()
    for category in ANALYSIS_CATEGORIES:
        for item in hot_search.get(category, []):
            text = item.get("text", "")
            if len(text) < 6 or text in seen:
                continue
            merged.append({"text": text, "heat": item.get("heat", "")})
            seen.add(text)
    return merged[:LONG_TAIL_LIMIT]


def fetch_keyword_pool(query_group: int, request_name: str) -> list[dict[str, Any]]:
    payload = build_request_payload(first_category_id="", query_group=query_group)
    return fetch_with_best_effort(payload, request_name)


def build_api_keyword_sections(dt: datetime) -> dict[str, Any]:
    recommended_pool = fetch_keyword_pool(5, "推荐词")
    hot_pool = fetch_keyword_pool(2, "热搜词")
    blue_pool = fetch_keyword_pool(4, "蓝海词")

    rising_pending = False
    try:
        rising_pool = fetch_keyword_pool(1, "飙升词")
        if (
            keywords_signature(rising_pool) == keywords_signature(hot_pool)
            or keywords_signature(rising_pool) == keywords_signature(blue_pool)
            or keywords_signature(rising_pool) == keywords_signature(recommended_pool)
        ):
            rising_pending = True
            stderr("[xhs] 飙升词 queryGroup=1 返回结果与其他词池重复，需再次核对参数，已回退为按涨幅规则筛选。")
            rising_pool = hot_pool
    except Exception as exc:  # noqa: BLE001
        rising_pending = True
        stderr(f"[xhs] 飙升词 queryGroup=1 抓取失败，改用热搜词按涨幅规则筛选：{exc}")
        rising_pool = hot_pool

    recommended = pick_recommended_from_pool(recommended_pool)
    hot_search = assign_keywords_from_generic_pool(hot_pool, dt)
    blue_ocean = pick_blue_ocean_from_pool(blue_pool)
    rising = pick_rising_from_pool(rising_pool)
    long_tail = pick_long_tail_from_hot_search(hot_search)

    return {
        "recommended": recommended,
        "hot_search": hot_search,
        "blue_ocean": blue_ocean,
        "rising": rising,
        "long_tail": long_tail,
        "rising_query_group_pending": rising_pending,
    }


def build_fallback_keyword_sections(dt: datetime) -> dict[str, Any]:
    hot_search = {
        category: [strip_keyword_fields(item) for item in build_category_words(category, dt)]
        for category in ANALYSIS_CATEGORIES
    }
    merged_pool = []
    seen = set()
    for category in ANALYSIS_CATEGORIES:
        for item in build_category_words(category, dt):
            if item["text"] in seen:
                continue
            merged_pool.append(item)
            seen.add(item["text"])
    recommended = pick_recommended_from_pool(merged_pool)
    blue_ocean = pick_blue_ocean_from_pool(merged_pool)
    rising = pick_rising_from_pool(merged_pool)
    long_tail = pick_long_tail_from_hot_search(hot_search)
    return {
        "recommended": recommended,
        "hot_search": hot_search,
        "blue_ocean": blue_ocean,
        "rising": rising,
        "long_tail": long_tail,
        "rising_query_group_pending": True,
    }


def build_keyword_sections(dt: datetime) -> dict[str, Any]:
    """生成关键词分区数据。

    为规避账号违规风险：
    - 已禁用任何真实接口抓取；
    - 直接使用规则生成（fallback）逻辑。
    """

    stderr("[xhs] 已禁用真实接口抓取，直接使用规则生成（fallback）逻辑。")
    return build_fallback_keyword_sections(dt)


def main() -> None:
    dt = now_cn()
    sections = build_keyword_sections(dt)
    keywords = {
        "updated_at": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "recommended": sections["recommended"],
        "hot_search": sections["hot_search"],
        "blue_ocean": sections["blue_ocean"],
        "rising": sections["rising"],
        "long_tail": sections["long_tail"],
        "activities": month_activities(dt)[:8],
    }
    write_json(KEYWORDS_PATH, keywords)
    history = update_history(dt, keywords)
    write_json(HISTORY_PATH, history)

    templates = load_templates()
    templates = refresh_templates(templates, dt)
    write_json(TEMPLATES_PATH, templates)

    print("keywords.json updated:", KEYWORDS_PATH)
    print("history.json updated:", HISTORY_PATH)
    print("templates.json updated:", TEMPLATES_PATH)
    print("updated_at:", keywords["updated_at"])
    print("rising_query_group_pending:", sections.get("rising_query_group_pending", False))


if __name__ == "__main__":
    main()
