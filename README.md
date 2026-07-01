# Multimodal Chatbot with Memory Management

这是一个基于 LangChain 和 Gradio 构建的多模态聊天机器人应用。该项目不仅支持文本交互，还集成了图片、音频和视频等多模态输入能力。同时，项目实现了基于 SQLite 的持久化会话记忆，并内置了上下文摘要（Context Summarization）机制，有效解决了长对话中的 Token 溢出问题。

## 核心特性

- **多模态交互**：基于 Gradio `MultimodalTextbox`，支持用户同时输入文本并上传多张图片、音频（`.wav`）或视频（`.mp4`）文件。
- **持久化会话记忆**：使用 LangChain 的 `SQLChatMessageHistory` 将聊天记录持久化到 SQLite 数据库，支持多会话隔离。
- **智能上下文摘要**：内置滑动窗口与摘要机制，自动保留最近 2 条核心对话，并将历史对话压缩为摘要，大幅节省 Token 消耗。
- **动态系统提示词**：根据是否存在历史摘要，动态构建 System Prompt，确保 AI 能够精准理解长上下文。
- **优雅的前后端状态同步**：完善的异常处理与状态机设计，AI 回复期间自动锁定输入框，回复完成后自动解锁。

## ️ 技术栈

- **AI 编排框架**：LangChain
- **前端 UI**：Gradio
- **数据存储**：SQLite (通过 SQLAlchemy)
- **大语言模型**：Qwen (通义千问)

## 环境依赖

在运行此项目之前，请确保您的环境中已安装以下 Python 依赖：

```bash
pip install langchain langchain-community gradio sqlalchemy
```

**注意**：请确保您已经在 `models.py` 中正确配置了 Qwen 模型的实例（例如 `qwen = ChatOpenAI(...)`），并在项目根目录下创建了 `models.py` 文件。

## 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd <your-repo-name>
```

### 2. 准备模型配置

在项目根目录下创建 `models.py`，并初始化您的大模型：

```python
# models.py
from langchain_openai import ChatOpenAI

qwen = ChatOpenAI(
    model="qwen-turbo",
    openai_api_key="your-api-key",
    openai_api_base="your-base-url"
)
```

### 3. 运行应用

```bash
python ai_chat_bot.py
```

启动后，终端会输出一个本地 URL（通常为 `http://127.0.0.1:7860`），在浏览器中打开即可体验。

## ️ 核心架构解析

### 1. 上下文摘要机制 (Context Summarization)

为了避免长对话导致的 Token 超限，项目实现了 `summarize_messages` 函数：

- 当历史记录 $\le 2$ 条时，直接传递原始消息。
- 当历史记录 $> 2$ 条时，提取除最后 2 条外的所有消息，调用 LLM 生成核心摘要。
- 将 `摘要 + 最近 2 条原始消息` 作为最终的 `chat_history` 注入给 LLM。

### 2. 多模态消息解析

在 `add_message` 和 `respond` 函数中，对 Gradio 传入的复杂数据结构进行了标准化处理：

- 自动识别 `content` 是纯文本还是包含 `type: text/file` 的多模态列表。
- 提取文件路径并安全地传递给后端处理逻辑。

## 项目结构

```text
.
├── ai_chat_bot.py      # 主程序入口 (Gradio UI + 核心业务逻辑)
├── models.py           # LLM 模型实例配置
├── chat_history.db     # SQLite 聊天记录数据库 (运行后自动生成)
└── README.md           # 项目说明文档
```

## 贡献指南

欢迎提交 Issue 或 Pull Request 来完善此项目！如果您希望扩展新的工具（如联网搜索、数据库查询）或接入 LangSmith 监控，请参考 LangChain 官方文档进行扩展。

