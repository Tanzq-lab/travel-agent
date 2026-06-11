from __future__ import annotations

from hashlib import sha1

from app.collectors.base import SourceCollector
from app.schemas import RawDocument

KNOWN_MOCK_DESTINATIONS = {"重庆", "成都"}


MOCK_DOCUMENTS: list[dict] = [
    {
        "id": "cq-july-heat",
        "destination": "重庆",
        "platform": "xhs",
        "title": "7月重庆避暑避坑：白天热，晚上江边好",
        "url": "https://mock.local/xhs/cq-july-heat",
        "author": "山城慢游记",
        "publish_time": "2026-06-01",
        "like_count": 381,
        "collect_count": 219,
        "comment_count": 64,
        "content": (
            "7月重庆真的很热，白天不建议一直在户外走。洪崖洞晚上好看，"
            "但是人特别多，拍照很挤。带爸妈建议白天安排三峡博物馆、商场、"
            "轻轨路线，晚上再去江边，节奏会轻松很多。"
        ),
        "evidences": [
            {
                "place_name": None,
                "place_type": None,
                "topic": "季节风险",
                "sentiment": "negative",
                "claim": "7月重庆白天户外游玩体验较差",
                "reason": "资料提到天气很热，不建议白天长时间在户外走。",
                "suitable_for": [],
                "not_suitable_for": ["怕热", "带父母", "不喜欢太累"],
                "mentioned_season": "7月",
                "warning": "白天不建议一直在户外走。",
                "confidence": 0.9,
            },
            {
                "place_name": "洪崖洞",
                "place_type": "景点",
                "topic": "景点避坑",
                "sentiment": "negative",
                "claim": "洪崖洞夜景好看但拥挤",
                "reason": "资料提到晚上好看，但人特别多，拍照很挤。",
                "suitable_for": ["能接受排队和拥挤的夜景游客"],
                "not_suitable_for": ["怕挤", "带老人", "想轻松拍照"],
                "mentioned_season": "7月",
                "warning": "人多、拍照拥挤。",
                "confidence": 0.86,
            },
            {
                "place_name": "三峡博物馆",
                "place_type": "景点",
                "topic": "亲子长辈友好",
                "sentiment": "positive",
                "claim": "三峡博物馆适合炎热白天和长辈同行",
                "reason": "资料建议带爸妈白天安排三峡博物馆、商场和轻轨路线。",
                "suitable_for": ["带父母", "怕热", "不喜欢太累"],
                "not_suitable_for": [],
                "mentioned_season": "7月",
                "confidence": 0.82,
            },
        ],
    },
    {
        "id": "cq-three-days",
        "destination": "重庆",
        "platform": "zhihu",
        "title": "重庆三天两晚轻松路线复盘",
        "url": "https://mock.local/zhihu/cq-three-days",
        "author": "旅行路线研究员",
        "publish_time": "2026-05-18",
        "like_count": 212,
        "collect_count": 145,
        "comment_count": 31,
        "content": (
            "三天玩重庆不要贪多。第一天解放碑、来福士、洪崖洞夜景；"
            "第二天鹅岭二厂、李子坝轻轨、观音桥美食；第三天三峡博物馆、"
            "人民大礼堂和江边散步。路线用地铁串联，少爬坡会舒服。"
        ),
        "evidences": [
            {
                "place_name": None,
                "place_type": "路线",
                "topic": "游玩天数",
                "sentiment": "positive",
                "claim": "重庆三天两晚可以安排轻松路线",
                "reason": "资料给出三天分区路线，并提醒不要贪多。",
                "suitable_for": ["第一次去重庆", "不想太累"],
                "not_suitable_for": [],
                "mentioned_duration": "3天",
                "transportation_info": "用地铁串联，减少爬坡。",
                "confidence": 0.84,
            },
            {
                "place_name": "李子坝轻轨",
                "place_type": "景点",
                "topic": "景点推荐",
                "sentiment": "positive",
                "claim": "李子坝轻轨适合作为重庆特色打卡点",
                "reason": "资料把李子坝轻轨纳入第二天路线，并建议用地铁串联。",
                "suitable_for": ["拍照", "第一次去重庆"],
                "not_suitable_for": [],
                "transportation_info": "地铁可达。",
                "confidence": 0.78,
            },
            {
                "place_name": "观音桥",
                "place_type": "商圈",
                "topic": "美食",
                "sentiment": "positive",
                "claim": "观音桥适合安排美食和晚间活动",
                "reason": "资料将观音桥美食放在第二天路线中。",
                "suitable_for": ["美食", "夜间活动"],
                "not_suitable_for": [],
                "confidence": 0.76,
            },
        ],
    },
    {
        "id": "cq-stay-traffic",
        "destination": "重庆",
        "platform": "xhs",
        "title": "重庆住宿交通建议：别只看直线距离",
        "url": "https://mock.local/xhs/cq-stay-traffic",
        "author": "地铁旅行派",
        "publish_time": "2026-04-25",
        "like_count": 298,
        "collect_count": 251,
        "comment_count": 49,
        "content": (
            "重庆住宿建议优先看地铁站，不要只看地图直线距离。解放碑交通方便但价格高，"
            "观音桥吃饭方便，沙坪坝性价比高但去热门夜景点更远。山城坡多，"
            "带老人要少安排连续爬坡路线。"
        ),
        "evidences": [
            {
                "place_name": "解放碑",
                "place_type": "住宿区域",
                "topic": "住宿",
                "sentiment": "neutral",
                "claim": "解放碑交通方便但住宿价格偏高",
                "reason": "资料提到解放碑交通方便但价格高。",
                "suitable_for": ["第一次去重庆", "预算较充足"],
                "not_suitable_for": ["预算有限"],
                "mentioned_budget": "偏高",
                "transportation_info": "交通方便。",
                "confidence": 0.8,
            },
            {
                "place_name": "观音桥",
                "place_type": "住宿区域",
                "topic": "住宿",
                "sentiment": "positive",
                "claim": "观音桥适合重视吃饭便利的游客",
                "reason": "资料提到观音桥吃饭方便。",
                "suitable_for": ["美食", "中等预算"],
                "not_suitable_for": [],
                "transportation_info": "商圈餐饮集中。",
                "confidence": 0.77,
            },
            {
                "place_name": None,
                "place_type": None,
                "topic": "体力风险",
                "sentiment": "negative",
                "claim": "重庆山城坡多，带老人不宜连续爬坡",
                "reason": "资料明确提醒山城坡多，带老人要少安排连续爬坡路线。",
                "suitable_for": [],
                "not_suitable_for": ["带老人", "带父母", "不喜欢太累"],
                "transportation_info": "优先选择地铁站附近住宿。",
                "warning": "不要只按地图直线距离判断路程。",
                "confidence": 0.88,
            },
        ],
    },
    {
        "id": "cq-budget",
        "destination": "重庆",
        "platform": "tieba",
        "title": "重庆三天中等预算够不够",
        "url": "https://mock.local/tieba/cq-budget",
        "author": "预算党",
        "publish_time": "2026-03-30",
        "like_count": 95,
        "collect_count": 42,
        "comment_count": 28,
        "content": (
            "重庆三天中等预算一般够用，住宿选观音桥或沙坪坝会比解放碑更稳。"
            "主要花费在住宿、打车和火锅，景点门票压力不大。两三个人分摊住宿和交通会更划算。"
        ),
        "evidences": [
            {
                "place_name": None,
                "place_type": None,
                "topic": "预算",
                "sentiment": "positive",
                "claim": "重庆三天中等预算一般够用",
                "reason": "资料提到主要花费在住宿、打车和火锅，景点门票压力不大。",
                "suitable_for": ["中等预算", "三天行程"],
                "not_suitable_for": [],
                "mentioned_budget": "中等预算",
                "mentioned_duration": "3天",
                "confidence": 0.81,
            },
            {
                "place_name": "沙坪坝",
                "place_type": "住宿区域",
                "topic": "住宿",
                "sentiment": "neutral",
                "claim": "沙坪坝住宿性价比高但离热门夜景点更远",
                "reason": "资料建议预算控制时可考虑沙坪坝，但交通距离更远。",
                "suitable_for": ["预算有限", "中等预算"],
                "not_suitable_for": ["想住核心夜景区"],
                "mentioned_budget": "性价比高",
                "transportation_info": "去热门夜景点更远。",
                "confidence": 0.72,
            },
        ],
    },
    {
        "id": "cq-attraction-tradeoff",
        "destination": "重庆",
        "platform": "bilibili",
        "title": "重庆热门景点取舍：索道、磁器口和夜景",
        "url": "https://mock.local/bilibili/cq-attraction-tradeoff",
        "author": "城市体验剪辑",
        "publish_time": "2026-04-10",
        "like_count": 512,
        "collect_count": 280,
        "comment_count": 88,
        "content": (
            "长江索道体验有山城特色，但旺季排队很久，不一定适合带老人。"
            "磁器口商业化明显，时间紧可以不去。南滨路和江北嘴夜景更开阔，"
            "晚上去比白天暴晒时舒服。"
        ),
        "evidences": [
            {
                "place_name": "长江索道",
                "place_type": "景点",
                "topic": "景点避坑",
                "sentiment": "negative",
                "claim": "长江索道有特色但排队风险高",
                "reason": "资料提到旺季排队很久，不一定适合带老人。",
                "suitable_for": ["能接受排队的游客"],
                "not_suitable_for": ["带老人", "不喜欢太累"],
                "warning": "旺季排队很久。",
                "confidence": 0.83,
            },
            {
                "place_name": "磁器口",
                "place_type": "景点",
                "topic": "景点取舍",
                "sentiment": "neutral",
                "claim": "磁器口商业化明显，时间紧可以不去",
                "reason": "资料明确说时间紧可以不去。",
                "suitable_for": ["时间充裕"],
                "not_suitable_for": ["三天紧凑行程", "不喜欢商业街"],
                "warning": "商业化明显。",
                "confidence": 0.79,
            },
            {
                "place_name": "南滨路",
                "place_type": "景点",
                "topic": "夜景",
                "sentiment": "positive",
                "claim": "南滨路和江北嘴适合晚上看开阔夜景",
                "reason": "资料提到夜景更开阔，晚上去比白天舒服。",
                "suitable_for": ["夜景", "怕热"],
                "not_suitable_for": [],
                "mentioned_season": "夏季",
                "confidence": 0.82,
            },
        ],
    },
    {
        "id": "cd-food-photo",
        "destination": "成都",
        "platform": "xhs",
        "title": "成都三天美食拍照路线",
        "url": "https://mock.local/xhs/cd-food-photo",
        "author": "蓉城周末",
        "publish_time": "2026-05-08",
        "like_count": 188,
        "collect_count": 120,
        "comment_count": 22,
        "content": (
            "成都三天可以围绕春熙路、太古里、宽窄巷子和熊猫基地安排。"
            "美食集中，拍照点多，但宽窄巷子节假日人多，熊猫基地建议早去。"
        ),
        "evidences": [
            {
                "place_name": "太古里",
                "place_type": "商圈",
                "topic": "拍照",
                "sentiment": "positive",
                "claim": "太古里适合拍照和逛街",
                "reason": "资料把春熙路、太古里列为三天路线核心。",
                "suitable_for": ["拍照", "美食"],
                "not_suitable_for": [],
                "mentioned_duration": "3天",
                "confidence": 0.75,
            }
        ],
    },
]


class MockCollector(SourceCollector):
    """Deterministic local collector for demos and tests."""

    def __init__(self, platforms: list[str] | None = None) -> None:
        self.platforms = platforms or ["xhs", "zhihu", "bilibili", "weibo", "tieba"]

    def search(self, query: str, limit: int) -> list[RawDocument]:
        """Return local mock documents that match the query destination or terms."""

        matched: list[RawDocument] = []
        for item in MOCK_DOCUMENTS:
            if item["platform"] not in self.platforms:
                continue
            if not self._matches(query, item):
                continue
            doc_id = item["id"]
            matched.append(
                RawDocument(
                    id=doc_id,
                    platform=item["platform"],
                    query=query,
                    title=item["title"],
                    content=item["content"],
                    url=item["url"],
                    author=item["author"],
                    publish_time=item["publish_time"],
                    like_count=item["like_count"],
                    collect_count=item["collect_count"],
                    comment_count=item["comment_count"],
                    raw={
                        "mock_id": item["id"],
                        "destination": item["destination"],
                        "evidences": item.get("evidences", []),
                        "query_hash": sha1(query.encode("utf-8")).hexdigest()[:10],
                    },
                )
            )
            if len(matched) >= limit:
                break
        return matched

    @staticmethod
    def _matches(query: str, item: dict) -> bool:
        destination = item["destination"]
        if destination in query:
            return True
        query_destination = next((name for name in KNOWN_MOCK_DESTINATIONS if name in query), None)
        if query_destination and query_destination != destination:
            return False
        if "未知目的地" in query:
            return False
        query_terms = [term for term in query.replace("，", " ").split() if len(term) >= 2]
        searchable = f"{item['title']} {item['content']}"
        return any(term in searchable for term in query_terms)
