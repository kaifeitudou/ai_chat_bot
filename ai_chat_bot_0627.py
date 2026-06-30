import json
from langchain_community.chat_message_histories import SQLChatMessageHistory
# from langchain_sqlite import SQLiteChatMessageHistory
from langchain_core.prompts import MessagesPlaceholder, FewShotChatMessagePromptTemplate
from models import *
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import StrOutputParser, SimpleJsonOutputParser
from langchain_core.runnables import RunnableWithMessageHistory, RunnablePassthrough
from langchain_core.chat_history import InMemoryChatMessageHistory
import gradio as gr

# 1. 提示词模板
prompt = ChatPromptTemplate.from_messages([
    # ('system', '你是一个乐于助人的助手，尽你所能回答所有问题。提供的聊天历史包含与你对话用户的相关信息。'),
    ('system', '{system_message}'),
    MessagesPlaceholder(variable_name='chat_history', optional=True),
    ('human', '{input}')
])

chain = prompt | qwen

# 2. 存储聊天记录：（内存，关系型数据库或redis数据库
# 内存中
store = {} # 用来保存历史消息， key: 会话ID session_id

def get_session_history(session_id: str):
    """从内存中的历史消息列表中返回当前会话的所有历史消息"""
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()

    return store[session_id]

def get_redis_session_history(session_id: str):
    """从关系型数据库中的历史消息列表中返回当前会话的所有历史消息"""
    return SQLChatMessageHistory(
        session_id=session_id,
        connection='sqlite:///chat_history.db',
    )

# langchain 中所有的消息 SystemMessage, HumanMessage, AIMessage, ToolMessage
# 3.创建带历史记录功能的处理链
chain_with_message_history = RunnableWithMessageHistory(
    chain,
    get_redis_session_history,
    input_messages_key='input',
    history_messages_key='chat_history',
)

# 剪辑和摘要上下文，历史记录。保留最近的前2条消息，把之前所有的消息形成摘要
# def summarize_messages(current_input):
def summarize_messages(session_id: str):
    """剪辑和摘要上下文，历史记录"""
    # session_id = current_input['config']['configurable']['session_id']
    # if not session_id:
    #     raise ValueError("必须通过config参数提供session_id")

    # 获取当前会话ID的所有历史聊天记录
    chat_history = get_session_history(session_id)
    stored_messages = chat_history.messages

    if len(stored_messages) <= 2:
        return None, stored_messages
        # return {'original_messages': stored_messages, 'summary': None}

    # 剪辑消息列表
    last_two_message = stored_messages[-2:] # 保留的信息
    message_to_summarize = stored_messages[:-2] # 需要进行摘要的信息

    # 生成摘要提示词
    summarization_prompt = ChatPromptTemplate.from_message([
        ("system", "请将下边对话历史压缩为保留关键信息的摘要信息"),
        # ("placeholder", "{chat_history}"),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "请生成包含上述对话核心内容的摘要，保留重要事实和决策")
    ])

    summarization_chain = summarization_prompt | qwen
    # 生成摘要
    summary_message = summarization_chain.invoke({'chat_history': message_to_summarize})
    print("summary")
    print(summary_message)

    # 重建历史记录： 摘要 + 最后2条原始信息
    # chat_history.clear()
    # chat_history.add_message(summary_message)
    # for msg in last_two_message:
    #     chat_history.add_message(msg)

    # return True
    # 返回结构化结果
    return summary_message.content, last_two_message
    # return {
    #     "original_messages": last_two_message,
    #     "summary": summary_message
    # }

# 1.4 核心执行函数
def execute_chain(user_message: str, session_id: str):
    history = get_redis_session_history(session_id)
    # 1获取摘要和需要保留的最近信息
    summary, recent_messages = summarize_messages(session_id)
    # 2钩爪系统提示词
    if summary:
        system_msg = f"你是一个乐于助人的助手，尽你所能回答所有问题，之前的对话摘要：{summary}。"
    else:
        system_msg = f"你是一个乐于助人的助手，尽你所能回答所有问题。"
    # 3调用llm
    chain = prompt | qwen
    result = chain.invoke({
        "system_message": system_msg,
        "chat_history": recent_messages,
        "input": user_message
    })
    # 4.将新消息存入历史
    history.add_user_message(user_message)
    history.add_ai_message(result.content)

    return result.content

# 数据格式转换
def sync_history_to_store(gradio_history: list, session_id: str):
    """确保内存store中的历史与gradio前端同步"""
    history = get_redis_session_history(session_id)
    history.clear()
    for msg in gradio_history:
        content = msg.get("content", "")
        if isinstance(content, list):
            # content = "".join(join[item["text"] for item in content if item.get("type") == "text"])
            text_content = "".join(
                [item.get("text", "") for item in content if isinstance(item, dict) and "text" in item])
        else:
            text_content = content

        if msg["role"] == "user":
            history.add_user_message(content)
        elif msg["role"] == "assistant":
            history.add_ai_message(content)

def add_message(history, messages):
    """将用户输入的消息添加到聊天记录中"""
    text = ""
    files = []

    print(messages)
    print(history)
    if isinstance(messages, dict):
        text = messages.get('text', '')
        files = messages.get('files', [])
    else:
        # 方案B: 通常在 .submit 事件中，Gradio 会自动解包
        # 这里我们假设 history 是 chatbot 的值，new_message 是 textbox 的值（纯文本或包含属性的对象）
        text = str(messages) if messages is not None else ""
        files = []
    message_parts = []
    # add text
    if text:
        message_parts.append({"type": "text", "text": text})
    # 处理文件（图片/音频路径）
    if files:
        for file in files:
            # file 可能是字符串路径，也可能是包含 'path' 的对象
            file_path = file if isinstance(file, str) else getattr(file, 'path', None) #file.get('path', '')
            if file_path:
                message_parts.append({
                    "type": "file",
                    "file": {"path": file_path}
                })
                # history.append({"role": "user", "content": f"[文件]: {file_path}"})

    # 处理文本
    if message_parts:
        history.append({"role": "user", "content": message_parts})

    # for m in messages['files']:
    #     print(m)
    #     history.append({'role': 'user', "content":{'path': m}})
    #
    # if messages['text'] is not None:
    #     history.append({'role': 'user', 'content': messages['text']})

    return history, gr.MultimodalTextbox(value=None, interactive=False)

def get_last_user_after_assistant(history):
    if not history:
        return None
    if history[-1]["role"] == "assistant":
        return None

    last_assistant_idx = -1
    for i in range(len(history)-1, -1, -1):
        if history[i]["role"] == "assistant":
            last_assistant_idx = 1
            break

    if last_assistant_idx == -1:
        return history
    else:
        return history[last_assistant_idx+1:]
def submit_message(history):
    """提交用户输入的信息，生成机器人回复"""
    user_messages = get_last_user_after_assistant(history)
    print(user_messages)
    chat_history, _ = respond(user_messages, history)
    print(chat_history)
    return chat_history


# def respond(user_message: str, chat_history: list):
def respond(history):
    '''session_id = "user123"

    # 1 将前端传来的完整历史同步到后端store
    sync_history_to_store(chat_history, session_id)

    # 2 调用核心逻辑
    ai_response = execute_chain(user_message, session_id)

    # 3 更新前端显示
    chat_history.append({"role": "user", "content": user_message})
    chat_history.append({"role": "assistant", "content": ai_response})

    return chat_history, ""'''
    if history and history[-1]["role"] == "user":
        # 提取最后一条用户消息的文本内容
        last_msg = history[-1]["content"]
        user_input = ""

        if isinstance(last_msg, list):
            # 从多模态块中提取文本
            for part in last_msg:
                if isinstance(part, dict) and part.get("type") == "text":
                    user_input += part.get("text", "")
        else:
            user_input = str(last_msg)

        # 调用核心链
        try:
            ai_response = execute_chain(user_input, "user123")
            history.append({"role": "assistant", "content": ai_response})
        except Exception as e:
            history.append({"role": "assistant", "content": f"发生错误: {str(e)}"})
    return history

def unlock_input():
    """AI 回复完成后，重新启用输入框供用户继续输入"""
    return gr.MultimodalTextbox(interactive=True)

# 开发聊天机器人web界面
with gr.Blocks(title='多模态聊天机器人', theme=gr.themes.Soft()) as block:
    # 聊天历史记录的组件
    chatbot = gr.Chatbot(height=500, label='聊天机器人')

    # 创建多模态输入框
    chat_input = gr.MultimodalTextbox(
        interactive=True,
        file_types=['image', '.wav', '.mp4'],
        file_count="multiple",
        placeholder="请输入信息或上传文件",
        show_label=False,
        sources=["microphone", "upload"],
    )

    chat_msg = chat_input.submit(add_message, [chatbot, chat_input], [chatbot, chat_input])
    # chat_msg.then(submit_message, [chatbot], [chatbot])
    chat_msg.then(respond, [chatbot], [chatbot])
    chat_msg.then(
        unlock_input,
        inputs=None,
        outputs=[chat_input]
    )

    # 绑定事件
    # submit_btn.click(respond, [user_input, chatbot], [chatbot, user_input])
    # user_input.submit(respond, [user_input, chatbot], [chatbot, user_input])
    # chat_msg = user_input.submit(add_messages, [chatbot, user_input], [chatbot, user_input])
    # chat_msg.then(execute_chain, chatbot, chatbot)

if __name__ == '__main__':
    block.launch()
