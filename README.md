# Media Tool - 多模态资讯展示工具

自动化多模态资讯展示工具，支持从主题选择到多种格式输出的完整流水线。

## 功能

1. **主题选择** — 自定义输入 / AI 热点推荐
2. **素材采集** — 手动提供 URL / AI 自动搜索
3. **内容结构化** — AI 生成可编辑大纲
4. **多格式输出**
   - 📱 小红书风格图文卡片（5种风格）
   - 🖼️ 幻灯片图片 / PPT
   - 🎬 Remotion 视频
   - 🎙️ AI 播客（Edge TTS 语音合成）

## 技术栈

- **后端**: FastAPI + DeepSeek API
- **前端**: Streamlit
- **搜索**: DuckDuckGo
- **图片渲染**: Playwright
- **语音合成**: Edge TTS

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt
playwright install chromium

# 配置
cp .env.example .env
# 编辑 .env 填入 DeepSeek API Key

# 启动后端
uvicorn backend.server:app --port 8100

# 启动前端（新终端）
streamlit run app/main.py --server.port 8501
```

## 环境变量

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | API 地址（默认 https://api.deepseek.com） |
| `BACKEND_URL` | 后端地址（默认 http://localhost:8100） |
