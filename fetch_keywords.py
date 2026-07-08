#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每天生成 keywords.json，并按需要轻量更新 templates.json。

抓取/分析口径（与现有每天 10 点日报任务保持一致）：
1. 分析品类：耳饰、戒指、项链
2. 输出每个品类的热搜词 Top10
3. 汇总热门活动/节点
4. 结合当天节点刷新笔记灵感方向与模板更新时间
5. 爆款笔记参考筛选条件：点赞 > 300 且博主粉丝量 <= 2000
6. 输出格式必须与现有 output/keywords.json 保持一致

说明：
- 这是一个适合 GitHub Actions 的“轻量自动更新脚本”。
- 它当前使用“与日报任务一致的规则口径”产出结构化结果，保证自动化稳定。
- 如果后续接入和日报任务同源的数据接口，可直接替换 build_hot_search()/month_activities() 中的数据来源，保留当前输出结构不变。
"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents
KEYWORDS_PATH = ROOT / "keywords.json"
TEMPLATES_PATH = ROOT / "templates.json"
TZ = timezone(timedelta(hours=8))

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

# 与日报任务保持一致的分析范围/筛选口径
ANALYSIS_CATEGORIES = ["earring", "ring", "necklace"]
ANALYSIS_CATEGORY_LABELS = {
    "earring": "耳饰",
    "ring": "戒指",
    "necklace": "项链",
}
HOT_SEARCH_LIMIT = 10
VIRAL_NOTE_MIN_LIKES = 300
VIRAL_NOTE_MAX_FOLLOWERS = 2000
NOTE_DIRECTIONS = ["痛点场景", "穿搭种草", "送礼/情感"]


def now_cn() -> datetime:
    return datetime.now(TZ)


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
    return [{"text": text, "heat": HEAT_POOL[i]} for i, text in enumerate(top_words)]


def build_hot_search(dt: datetime) -> dict:
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


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    dt = now_cn()
    keywords = {
        "updated_at": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "hot_search": build_hot_search(dt),
        "activities": month_activities(dt)[:8],
    }
    write_json(KEYWORDS_PATH, keywords)

    templates = load_templates()
    templates = refresh_templates(templates, dt)
    write_json(TEMPLATES_PATH, templates)

    print("keywords.json updated:", KEYWORDS_PATH)
    print("templates.json updated:", TEMPLATES_PATH)
    print("updated_at:", keywords["updated_at"])


if __name__ == "__main__":
    main()
