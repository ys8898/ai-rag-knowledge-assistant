import os
import logging
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
# 加载环境变量
load_dotenv()
from llm.qwen import ask_qwen
from database.db import init_db, save_message
from knowledge_sync import sync_knowledge
from knowledge_manager import (
    list_documents,
    delete_document,
    save_document,
)
from rag.search import search_vector, small_talk_reply
from rag.index_integrity import VectorStoreConsistencyError
from llm.query_rewrite import rewrite_question
from database.db import get_history
from rag.need_rewrite import need_rewrite
import json
import time

logger = logging.getLogger(__name__)

print(
    "当前目录:",
    os.getcwd()
)


#创建应用实例
app = FastAPI()


@app.exception_handler(VectorStoreConsistencyError)
async def vector_store_consistency_error_handler(request, error):
    return JSONResponse(
        status_code=503,
        content={
            "code": "vector_store_inconsistent",
            "detail": str(error),
        },
    )

#添加 CORS 中间件
app.add_middleware(

    CORSMiddleware,

    allow_origins=[
        "http://localhost:5173"
        "http://116.62.224.244"
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


def format_sse_event(event_type, data):

    return (
        f"event: {event_type}\n"
        f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
    )


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

    changes = save_document(
        filename,
        file.file,
        sync_knowledge,
    )


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
    try:
        result = delete_document(
            filename,
            sync_knowledge,
        )
    except VectorStoreConsistencyError:
        raise
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_knowledge_filename",
                "message": str(error),
            },
        ) from error
    except Exception as error:
        logger.exception("Knowledge document deletion failed: %s", filename)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "knowledge_delete_failed",
                "message": "知识库文件删除失败",
                "reason": str(error),
            },
        ) from error

    if result:

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

        def generate_small_talk_events():

            for char in reply:

                yield format_sse_event(
                    "token",
                    {"text": char}
                )

                time.sleep(0.05)


        return StreamingResponse(
            generate_small_talk_events(),
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

            yield format_sse_event(
                "token",
                {"text": "知识库中没有相关信息。"}
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

            yield format_sse_event(
                "token",
                {"text": "知识库中没有足够信息回答该问题。"}
            )


        else:


            for text in ask_qwen(
                data.user_id,
                search_question,
                context
            ):


                yield format_sse_event(
                    "token",
                    {"text": text}
                )



        # ==========================
        # 最后发送 metadata
        # ==========================

        metadata={

            "sources":result["sources"],

            "confidence":confidence

        }


        yield format_sse_event(
            "metadata",
            metadata
        )



    return StreamingResponse(

        generate(),

        media_type="text/event-stream"

    )

