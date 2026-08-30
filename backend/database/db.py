import sqlite3


# =========================
# 初始化数据库
# =========================
def init_db():

    # 连接SQLite数据库
    # 如果不存在，会自动创建 chat.db 文件
    conn = sqlite3.connect(
        "chat.db"
    )

    # 创建游标
    # 游标负责执行SQL语句
    cursor = conn.cursor()


    # =========================
    # 创建聊天记录表
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages(

        
        id INTEGER PRIMARY KEY AUTOINCREMENT,


        user_id TEXT,

        role TEXT,

        content TEXT

    )
    """)

    # =========================
    # 创建知识库文件记录表
    # =========================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS knowledge_files(

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    filename TEXT,

    file_type TEXT,

    file_size INTEGER,

    upload_time TEXT,

    chunk_count INTEGER,

    file_hash TEXT

    )
    """)


    # 提交数据库修改
    conn.commit()


    # 关闭连接
    conn.close()



# =========================
# 保存聊天消息
# =========================
def save_message(
    user_id,
    role,
    content
):

    conn = sqlite3.connect(
        "chat.db"
    )


    cursor = conn.cursor()


    # 插入一条聊天记录
    cursor.execute(
        """
        INSERT INTO messages
        (
            user_id,
            role,
            content
        )

        VALUES (?, ?, ?)
        """,
        (
            user_id,
            role,
            content
        )
    )


    # 保存修改
    conn.commit()


    # 关闭连接
    conn.close()



# =========================
# 获取历史聊天记录
# =========================
def get_history(
    user_id,
    limit=10
):

    conn = sqlite3.connect(
        "chat.db"
    )


    cursor = conn.cursor()


    # 查询指定用户的所有历史消息
    # 按id排序，保证聊天顺序
    cursor.execute(
        """
        SELECT role,content
        FROM messages
        WHERE user_id=?
        ORDER BY id DESC
        LIMIT ?
        """,
        (
            user_id,
            limit*2
        )
    )


    rows = cursor.fetchall()


    conn.close()

    rows = rows[::-1]

    history=[]


    # SQLite返回:
    #
    # [
    #   ("user","你好"),
    #   ("assistant","您好")
    # ]
    #
    # 转换成OpenAI需要的格式:
    #
    # [
    #   {
    #      "role":"user",
    #      "content":"你好"
    #   }
    # ]
    

    for row in rows:

        history.append(
            {
                "role":row[0],
                "content":row[1]
            }
        )


    return history


#保存知识文件信息
def save_knowledge_file(
    filename,
    file_type,
    file_size,
    chunk_count,
    file_hash
):

    conn = sqlite3.connect(
        "chat.db"
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        INSERT INTO knowledge_files
        (
            filename,
            file_type,
            file_size,
            upload_time,
            chunk_count,
            file_hash
        )

        VALUES (?, ?, ?, datetime('now'), ?,?)

        """,
        (
            filename,
            file_type,
            file_size,
            chunk_count,
            file_hash
        )
    )


    conn.commit()

    conn.close()


#查询知识文件
def get_knowledge_files():

    conn = sqlite3.connect(
        "chat.db"
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        SELECT
        filename,
        file_type,
        file_size,
        upload_time,
        chunk_count,
        file_hash

        FROM knowledge_files
        """
    )


    rows = cursor.fetchall()


    conn.close()


    files=[]


    for row in rows:

        files.append(
            {
                "filename":row[0],
                "file_type":row[1],
                "file_size":row[2],
                "upload_time":row[3],
                "chunk_count":row[4],
                "file_hash":row[5]
            }
        )


    return files

#删除记录
def delete_knowledge_file(
    filename
):

    conn = sqlite3.connect(
        "chat.db"
    )


    cursor = conn.cursor()


    cursor.execute(
        """
        DELETE FROM knowledge_files

        WHERE filename=?
        """,
        (
            filename,
        )
    )


    conn.commit()

    conn.close()

#替换旧同名文件
def delete_knowledge_file_by_name(
    filename
):

    conn = sqlite3.connect(
        "chat.db"
    )

    cursor = conn.cursor()


    cursor.execute(
        """
        DELETE FROM knowledge_files

        WHERE filename=?
        """,
        (
            filename,
        )
    )


    conn.commit()

    conn.close()


def update_knowledge_file(
    filename,
    file_type,
    file_size,
    chunk_count,
    file_hash
):
    """
    更新知识库文件记录

    如果文件原来存在：
        删除旧记录

    然后：
        写入最新记录
    """

    # 先删除同名旧记录
    delete_knowledge_file_by_name(
        filename
    )

    # 再保存最新记录
    save_knowledge_file(
        filename,
        file_type,
        file_size,
        chunk_count,
        file_hash
    )