from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.routes import router
from app.config import get_settings


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="资料驱动型旅游决策 Agent MVP",
)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    """Health endpoint used by local smoke tests."""

    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    """Human-readable API landing page for browser users."""

    return """
    <!doctype html>
    <html lang="zh-CN">
      <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Travel Agent MVP</title>
        <style>
          body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; line-height: 1.6; color: #172033; }
          main { max-width: 1120px; }
          label { display:block; margin-top: 14px; font-weight: 600; }
          textarea, input, select { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #c7ced8; border-radius: 6px; font: inherit; }
          textarea { min-height: 96px; }
          button { margin-top: 16px; padding: 10px 14px; border: 0; border-radius: 6px; background: #2457d6; color: white; font-weight: 700; cursor: pointer; }
          button:disabled { opacity: .6; cursor: wait; }
          .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
          .panel { border: 1px solid #d9dee7; border-radius: 8px; padding: 16px; margin-top: 18px; }
          .muted { color: #667085; }
          code, pre { background: #f4f6f8; border-radius: 6px; }
          code { padding: 2px 5px; }
          pre { padding: 16px; overflow: auto; }
          a { color: #2457d6; }
          @media (max-width: 800px) { .grid { grid-template-columns: 1fr; } body { margin: 18px; } }
        </style>
      </head>
      <body>
        <main>
          <h1>资料驱动型旅游 Agent MVP</h1>
          <p>输入旅行需求后，系统会搜索资料、抽取 evidence，再基于本次资料生成适配判断和攻略。API 文档见 <a href="/docs">/docs</a>。</p>
          <section class="panel">
            <label for="query">旅行需求</label>
            <textarea id="query">我要 7 月去重庆，玩 3 天，带爸妈，不喜欢太累，怕热，预算中等。</textarea>
            <div class="grid">
              <div>
                <label for="platforms">平台</label>
                <input id="platforms" value="xhs,zhihu,bilibili,weibo,tieba" />
              </div>
              <div>
                <label for="mode">采集模式</label>
                <select id="mode">
                  <option value="media_crawler">media_crawler</option>
                  <option value="auto">auto</option>
                  <option value="mock">mock</option>
                </select>
              </div>
            </div>
            <div class="grid">
              <div>
                <label for="limit">每个搜索词每个平台 limit</label>
                <input id="limit" type="number" min="1" max="50" value="5" />
              </div>
              <div>
                <label>&nbsp;</label>
                <button id="run">生成资料驱动报告</button>
              </div>
            </div>
            <p class="muted">media_crawler 需要先运行 <code>scripts/setup_media_crawler.ps1</code> 并按平台要求完成登录。未配置 OpenAI key 时会显示 fallback。</p>
          </section>

          <section class="panel">
            <h2>结果</h2>
            <div id="status" class="muted">尚未请求。</div>
            <pre id="meta"></pre>
            <pre id="report"></pre>
          </section>

          <h2>curl 示例</h2>
          <pre><code>curl -X POST http://127.0.0.1:8000/api/travel/plan \
  -H "Content-Type: application/json" \
  -d '{
    "user_query": "我要 7 月去重庆，玩 3 天，带爸妈，不喜欢太累，怕热，预算中等。",
    "platforms": ["xhs", "zhihu", "bilibili", "weibo", "tieba"],
    "collect_limit_per_query": 5,
    "collection_mode": "media_crawler"
  }'</code></pre>
        </main>
        <script>
          const run = document.getElementById('run');
          const statusEl = document.getElementById('status');
          const metaEl = document.getElementById('meta');
          const reportEl = document.getElementById('report');
          run.addEventListener('click', async () => {
            run.disabled = true;
            statusEl.textContent = '正在采集和生成报告...';
            metaEl.textContent = '';
            reportEl.textContent = '';
            try {
              const payload = {
                user_query: document.getElementById('query').value,
                platforms: document.getElementById('platforms').value.split(',').map(v => v.trim()).filter(Boolean),
                collect_limit_per_query: Number(document.getElementById('limit').value || 5),
                collection_mode: document.getElementById('mode').value
              };
              const response = await fetch('/api/travel/plan', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
              });
              const data = await response.json();
              if (!response.ok) throw new Error(JSON.stringify(data, null, 2));
              statusEl.textContent = `完成：${data.judgement.final_judgement}，${data.judgement.score}/100`;
              metaEl.textContent = JSON.stringify({
                request_id: data.request_id,
                collection_summary: data.collection_summary,
                collection_errors: data.collection_errors,
                llm_mode: data.llm_mode,
                evidence_summary: data.evidence_summary
              }, null, 2);
              reportEl.textContent = data.report;
            } catch (error) {
              statusEl.textContent = '请求失败';
              reportEl.textContent = String(error);
            } finally {
              run.disabled = false;
            }
          });
        </script>
      </body>
    </html>
    """
