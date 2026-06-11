from __future__ import annotations

import re

from app.schemas import QueryPlan, UserIntent


KNOWN_DESTINATIONS = [
    "重庆",
    "成都",
    "北京",
    "上海",
    "西安",
    "杭州",
    "广州",
    "深圳",
    "南京",
    "苏州",
    "厦门",
    "大理",
    "丽江",
    "三亚",
]

CHINESE_DIGITS = {
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}


class UserIntentParser:
    """Deterministic parser for common Chinese travel requests."""

    def parse(self, user_query: str) -> UserIntent:
        """Parse destination, dates, budget, companions, preferences, and constraints."""

        destination = self._parse_destination(user_query)
        days = self._parse_days(user_query)
        budget = self._parse_budget(user_query)
        budget_level = self._parse_budget_level(user_query)
        companions = self._parse_companions(user_query)
        preferences = self._parse_preferences(user_query)
        constraints = self._parse_constraints(user_query)
        travel_month = self._parse_month(user_query)
        return UserIntent(
            destination=destination,
            days=days,
            budget=budget,
            budget_level=budget_level,
            companions=companions,
            preferences=preferences,
            constraints=constraints,
            travel_month=travel_month,
        )

    @staticmethod
    def _parse_destination(text: str) -> str:
        for destination in KNOWN_DESTINATIONS:
            if destination in text:
                return destination
        match = re.search(r"去([\u4e00-\u9fa5]{2,8})", text)
        if match:
            value = re.split(r"[，,。；;\s]", match.group(1))[0]
            return value[:8]
        return "未知目的地"

    @staticmethod
    def _parse_month(text: str) -> int | None:
        match = re.search(r"(\d{1,2})\s*月", text)
        if not match:
            return None
        month = int(match.group(1))
        return month if 1 <= month <= 12 else None

    @staticmethod
    def _parse_days(text: str) -> int | None:
        digit_match = re.search(r"(\d{1,2})\s*天", text)
        if digit_match:
            return int(digit_match.group(1))
        chinese_match = re.search(r"([一二两三四五六七八九十])\s*天", text)
        if chinese_match:
            return CHINESE_DIGITS[chinese_match.group(1)]
        return None

    @staticmethod
    def _parse_budget(text: str) -> int | None:
        match = re.search(r"预算\s*(\d{3,6})", text)
        return int(match.group(1)) if match else None

    @staticmethod
    def _parse_budget_level(text: str) -> str | None:
        if "预算中等" in text or "中等预算" in text:
            return "中等预算"
        if "预算有限" in text or "穷游" in text:
            return "预算有限"
        if "预算充足" in text or "不差钱" in text:
            return "预算充足"
        return None

    @staticmethod
    def _parse_companions(text: str) -> list[str]:
        candidates = {
            "父母": ("爸妈", "父母", "家人"),
            "老人": ("老人", "长辈"),
            "朋友": ("朋友", "同学"),
            "情侣": ("情侣", "对象", "男朋友", "女朋友"),
            "孩子": ("孩子", "小孩", "亲子"),
        }
        return [label for label, words in candidates.items() if any(word in text for word in words)]

    @staticmethod
    def _parse_preferences(text: str) -> list[str]:
        candidates = ("拍照", "美食", "夜景", "轻松", "博物馆", "自然", "购物", "火锅", "人文")
        return [word for word in candidates if word in text]

    @staticmethod
    def _parse_constraints(text: str) -> list[str]:
        candidates = {
            "怕热": ("怕热", "不耐热"),
            "不喜欢太累": ("不喜欢太累", "不想太累", "轻松点"),
            "怕挤": ("怕挤", "不喜欢人多"),
            "预算有限": ("预算有限", "省钱"),
        }
        return [label for label, words in candidates.items() if any(word in text for word in words)]


class QueryPlanner:
    """Generate source-search queries across required travel decision categories."""

    def __init__(self, max_queries: int = 14) -> None:
        self.max_queries = max_queries

    def plan(self, intent: UserIntent) -> QueryPlan:
        """Create diverse search queries based on user intent."""

        destination = intent.destination
        duration = f"{intent.days}天" if intent.days else "第一次去"
        month = f"{intent.travel_month}月" if intent.travel_month else "适合几月去"
        budget = str(intent.budget) if intent.budget else intent.budget_level or "预算"

        queries = [
            f"{destination} {duration} 攻略",
            f"{destination} 第一次去 攻略",
            f"{destination} 避坑",
            f"{destination} {month} 季节 天气",
            f"{destination} 交通 攻略",
            f"{destination} 住宿区域 推荐",
            f"{destination} {budget} 预算 攻略",
            f"{destination} 必去 景点",
            f"{destination} 可去可不去 景点",
            f"{destination} 美食 推荐",
            f"{destination} 适合什么人 人群",
        ]

        for companion in intent.companions:
            queries.append(f"{destination} 带{companion} 轻松路线")
        for preference in intent.preferences:
            queries.append(f"{destination} {preference} 攻略")
        for constraint in intent.constraints:
            queries.append(f"{destination} {constraint} 避坑")

        return QueryPlan(destination=destination, queries=_dedupe(queries)[: self.max_queries])


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result

