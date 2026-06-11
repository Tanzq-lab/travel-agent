from app.agents.query_planner import QueryPlanner, UserIntentParser


def test_query_planner_covers_required_categories() -> None:
    parser = UserIntentParser()
    intent = parser.parse("我要 7 月去重庆，玩 3 天，带爸妈，不喜欢太累，怕热，预算中等。")
    plan = QueryPlanner(max_queries=20).plan(intent)
    joined = "\n".join(plan.queries)

    assert intent.destination == "重庆"
    assert intent.days == 3
    assert intent.travel_month == 7
    assert "父母" in intent.companions
    assert "怕热" in intent.constraints
    assert "攻略" in joined
    assert "避坑" in joined
    assert "季节" in joined
    assert "交通" in joined
    assert "住宿" in joined
    assert "预算" in joined
    assert "景点" in joined
    assert "美食" in joined
    assert "人群" in joined
    assert "怕热" in joined

