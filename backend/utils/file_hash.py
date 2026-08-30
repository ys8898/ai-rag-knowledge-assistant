import hashlib


def get_file_hash(path):
    """
    计算文件SHA256哈希值

    作用:
    判断两个文件内容是否完全一样

    参数:
    path:
        文件路径

    返回:
        SHA256字符串
    """


    sha256 = hashlib.sha256()


    # 二进制方式读取文件
    # 不一次性读入内存
    # 防止大文件占用过多
    with open(
        path,
        "rb"
    ) as f:


        while True:

            # 每次读取4KB
            chunk = f.read(4096)


            # 读取结束
            if not chunk:
                break


            # 更新hash计算
            sha256.update(chunk)


    return sha256.hexdigest()