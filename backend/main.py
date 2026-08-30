import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse  
# 加载环境变量
load_dotenv()
from llm.qwen import ask_qwen
from database.db import init_db, save_message
from knowledge_sync import sync_knowledge
import shutil
from knowledge_manager import (
    list_documents,
    delete_document
)
from rag.search import search_vector, small_talk_reply
from llm.query_rewrite import rewrite_question
from database.db import get_history
from rag.need_rewrite import need_rewrite
import json
from stream_utils import generate_small_talk

print(
    "当前目录:",
    os.getcwd()
)


#创建应用实例
app = FastAPI()

#添加 CORS 中间件
app.add_middleware(

    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173"
    ],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]

)

# 知识库目录
KNOWLEDGE_PATH = "knowledge"

#目录不存在就创建
os.makedirs(
    KNOWLEDGE_PATH,
    exist_ok=True
)

# 初始化数据库
init_db()

chat_histories={}

class ChatRequest(BaseModel):
    user_id: str
    question: str


@app.post("/chat")
def chat(data: ChatRequest):

    reply = small_talk_reply(
        data.question
    )


    if reply:

        save_message(data.user_id, "user", data.question)
        save_message(data.user_id, "assistant", reply)

        return {
            "answer": reply,
            "sources":[]
        }
    # =========================
    # 获取历史对话
    # =========================

    history = get_history(
        data.user_id
    )

    # =========================
    # 查询改写
    # =========================

    if need_rewrite(
        data.question,
        history
    ):

        search_question = rewrite_question(
            history,
            data.question
        )


    else:

        search_question = data.question



    print(
        "原问题:",
        data.question
    )

    print(
        "检索问题:",
        search_question
    )


    # =========================
    # 向量检索
    # =========================

    result = search_vector(
        search_question
    )


    # =========================
    # 没找到
    # =========================

    if not result["found"]:

        return {
            "answer": "知识库中没有相关信息。",
            "sources": [],
            "confidence": {
                "score": 0,
                "level": "low"
            }
        }


    context=result["context"]


    confidence=result["confidence"]

    # =========================
    # 根据置信度控制回答
    # =========================


    if confidence["level"] == "low":

        answer = "知识库中没有足够信息回答该问题。"

    elif confidence["level"] == "medium":

        answer = ask_qwen(
            data.user_id,
            search_question,
            context
        )

        answer = (
            "根据目前知识库信息：\n"
            + answer
        )


    else:

        answer = ask_qwen(
            data.user_id,
            search_question,
            context
        )


    return {

        "answer": answer,

        "sources": result["sources"],

        "confidence": result["confidence"]

    }


@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...)
):

    filename = os.path.basename(
        file.filename
    )

    file_path = os.path.join(
        KNOWLEDGE_PATH,
        filename
    )

    # 保存上传文件
    with open(
        file_path,
        "wb"
    ) as buffer:

        shutil.copyfileobj(
            file.file,
            buffer
        )

    changes = sync_knowledge()


    return {
        "message":"上传并更新知识库成功",
        "filename":filename,
        "changes":changes
    }


#查看知识库
@app.get("/documents")
def documents():

    return list_documents()


#删除知识文件
@app.delete("/documents/{filename}")
def remove_document(filename: str):

    result = delete_document(
        filename
    )

    if result:

        # 文件已经从 knowledge 目录删除
        # 同步知识库
        sync_knowledge()

        return {
            "message": "删除成功"
        }

    raise HTTPException(
        status_code=404,
        detail="文件不存在"
    )


#流式输出

@app.post("/chat/stream")
def chat_stream(data: ChatRequest):

    # =========================
    # 闲聊检测
    # =========================

    reply = small_talk_reply(
        data.question
    )


    if reply:


        save_message(
            data.user_id,
            "user",
            data.question
        )


        save_message(
            data.user_id,
            "assistant",
            reply
        )

        return StreamingResponse(
            generate_small_talk(reply),  
            media_type="text/event-stream"
        )

    history = get_history(
        data.user_id
    )


    if need_rewrite(
        data.question,
        history
    ):

        search_question = rewrite_question(
            history,
            data.question
        )

    else:

        search_question = data.question



    result = search_vector(
        search_question
    )


    if not result["found"]:


        def no_result():

            yield (
                "event: token\n"
                "data: 知识库中没有相关信息。\n\n"
            )


        return StreamingResponse(
            no_result(),
            media_type="text/event-stream"
        )



    context = result["context"]

    confidence = result["confidence"]


    def generate():


        # 低置信度直接返回

        if confidence["level"]=="low":

            yield (
                "event: token\n"
                "data: 知识库中没有足够信息回答该问题。\n\n"
            )


        else:


            for text in ask_qwen(
                data.user_id,
                search_question,
                context
            ):


                yield (
                    "event: token\n"
                    f"data: {text}\n\n"
                )



        # ==========================
        # 最后发送 metadata
        # ==========================

        metadata={

            "sources":result["sources"],

            "confidence":confidence

        }


        yield (

            "event: metadata\n"

            f"data:{json.dumps(metadata,ensure_ascii=False)}\n\n"

        )



    return StreamingResponse(

        generate(),

        media_type="text/event-stream"

    )

