# Travel Agent MVP

资料驱动型旅游决策 Agent MVP。用户输入目的地和约束后，系统会先规划搜索词、采集资料、清洗去重、抽取结构化 evidence，再基于 evidence 做适配判断并生成 Markdown 报告。

它不是普通旅游聊天助手：报告中的推荐、避坑、路线、住宿交通和预算判断必须绑定到本次收集到的资料。资料不足时，系统会明确输出“资料不足，暂不能判断”，不会用模型常识强行补结论。

## 功能链路

```text
用户输入
-> UserIntentParser
-> QueryPlanner
-> SourceCollector
-> Cleaner / Dedupe
-> EvidenceExtractor
-> SQLite + local vector store
-> RAG Retriever
-> DestinationJudge
-> ReportWriter
```

默认请求模式是 `media_crawler`：优先通过 MediaCrawler 做真实公开资料采集。没有安装 MediaCrawler 或平台登录失败时，响应会在 `collection_errors` 中透明说明。也可以使用 `collection_mode=auto` 自动降级到 mock。

## 安装

```bash
pip install -r requirements.txt
cp .env.example .env
```

Windows PowerShell 可以使用：

```powershell
Copy-Item .env.example .env
```

## 配置

`.env.example` 包含所有可用配置：

- `DATABASE_PATH`：SQLite 数据库路径，默认 `data/travel_agent.sqlite3`
- `VECTOR_STORE_PATH`：本地向量索引路径，默认 `data/vector_store`
- `DEFAULT_USE_MOCK`：兼容旧参数；新请求优先使用 `collection_mode`
- `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL`：预留 OpenAI-compatible live mode 配置
- `MEDIA_CRAWLER_ROOT`：MediaCrawler 本地路径，默认 `external/MediaCrawler`
- `MEDIA_CRAWLER_RUNNER`：MediaCrawler 运行器，默认 `uv run`
- `MEDIA_CRAWLER_LOGIN_TYPE`：登录方式，默认 `qrcode`
- `MEDIA_CRAWLER_SAVE_OPTION`：保存格式，默认 `jsonl`
- `MEDIA_CRAWLER_SLEEP_SECONDS` / `MEDIA_CRAWLER_RATE_LIMIT_PER_MINUTE`：采集限速配置

未配置 `OPENAI_API_KEY` 时，系统使用确定性 fallback 逻辑跑通 MVP。

## Codex Skill 使用

已创建项目内 Skill，随仓库一起移动：

```text
.codex/skills/travel-research-agent
```

在 Codex 中可以直接说：

```text
使用 $travel-research-agent 研究：我要 7 月去重庆，玩 3 天，带爸妈，不喜欢太累，怕热，预算中等。
```

Skill 会调用项目 CLI，不需要启动 Web 服务。请在仓库根目录运行：

```powershell
python scripts\run_travel_research.py "我要 7 月去重庆，玩 3 天，带爸妈，不喜欢太累，怕热，预算中等。" --collection-mode auto --limit 5
```

如果明确要真实采集：

```powershell
python scripts\run_travel_research.py "我要去重庆" --collection-mode media_crawler --limit 5
```

## 启动 FastAPI

```bash
uvicorn app.main:app --reload
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```

## API Demo

```bash
curl -X POST http://127.0.0.1:8000/api/travel/plan \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "我要 7 月去重庆，玩 3 天，带爸妈，不喜欢太累，怕热，预算中等。",
    "platforms": ["xhs", "zhihu", "bilibili", "weibo", "tieba"],
    "collect_limit_per_query": 5,
    "collection_mode": "media_crawler"
  }'
```

响应包含：

- `request_id`
- `intent`
- `queries`
- `collection_summary`
- `collection_errors`
- `llm_mode`
- `evidence_summary`
- `judgement`
- `report`

报告会明确写出“根据本次收集到的资料”，并基于 mock evidence 生成结论。

## 历史查询 API

```bash
curl http://127.0.0.1:8000/api/travel/report/{request_id}
curl http://127.0.0.1:8000/api/travel/evidences/{request_id}
```

## 数据结构

核心 schema 位于 `app/schemas.py`：

- `RawDocument`：统一采集结果，保留平台、URL、作者、时间、互动数和 raw payload。
- `TravelEvidence`：结构化旅游证据，包含 topic、sentiment、claim、reason、适合/不适合人群、季节、预算、交通和来源。
- `UserIntent`：目的地、天数、预算、同行人、偏好、约束和月份。
- `JudgeResult`：最终结论、分数、正负理由、人群判断、置信度和 evidence summary。

SQLite 会保存 raw documents、evidences 和 reports。本地向量检索会同时索引原文 chunk 与 structured evidence。

## 接入 MediaCrawler

本项目不导入、不修改 MediaCrawler 源码，只通过命令行子进程边界调用。

`external/MediaCrawler/` 被 `.gitignore` 忽略，不随主仓库提交。原因是它是第三方依赖，安装后会包含 `.venv`、Playwright 浏览器、缓存等本机生成文件，体积较大且跨机器不可复用。

换一台电脑 clone 本项目后，普通运行命令不会自动下载 MediaCrawler。需要先在仓库根目录执行初始化脚本；脚本会检测 `external/MediaCrawler` 是否存在，不存在时下载源码，并安装 Python 依赖和 Playwright 浏览器。

首次安装：

```powershell
.\scripts\setup_media_crawler.ps1
```

如果 `github.com` 连接失败，setup 脚本会尝试通过 GitHub codeload 源码压缩包兜底下载。安装完成后，`MEDIA_CRAWLER_ROOT` 默认指向 `external/MediaCrawler`。

示例配置：

```env
MEDIA_CRAWLER_ROOT=external/MediaCrawler
MEDIA_CRAWLER_RUNNER=uv run
MEDIA_CRAWLER_LOGIN_TYPE=qrcode
MEDIA_CRAWLER_SAVE_OPTION=jsonl
MEDIA_CRAWLER_SLEEP_SECONDS=1.5
MEDIA_CRAWLER_RATE_LIMIT_PER_MINUTE=8
```

请求时设置：

```json
{
  "collection_mode": "media_crawler",
  "platforms": ["xhs", "zhihu", "bilibili", "weibo", "tieba"],
  "collect_limit_per_query": 5
}
```

如果 `MEDIA_CRAWLER_ROOT` 不存在，API 会返回清晰的 `collection_errors`，不会自动启动大规模采集。

## 测试

```bash
pytest
```

覆盖内容：

- 搜索词生成是否覆盖攻略、避坑、季节、交通、住宿、预算、景点、美食、人群和用户偏好。
- evidence 抽取结果是否符合 schema 且保留来源 doc_id。
- 适配评分是否覆盖适合、条件适合、不适合、资料不足场景。

## 合规与安全

- 默认真实采集模式依赖本地 MediaCrawler 和平台登录态。
- `collection_mode=auto` 可以在 MediaCrawler 缺失时降级 mock。
- 采集必须设置 `limit`、sleep 和 rate limit。
- 不采集私密信息。
- 不绕过登录、付费墙、验证码或权限限制。
- 不存储敏感个人信息。
- 正式商业化需要使用合规数据源或用户授权数据。
