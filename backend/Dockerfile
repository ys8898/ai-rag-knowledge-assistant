FROM python:3.11


WORKDIR /app


COPY requirements.txt .


# 升级pip，使用国内源
RUN pip install --upgrade pip \
    -i https://mirrors.aliyun.com/pypi/simple/


# 安装CPU版PyTorch
RUN pip install \
    torch==2.3.1 \
    --index-url https://download.pytorch.org/whl/cpu


# 安装其他依赖
RUN pip install \
    -r requirements.txt \
    -i https://mirrors.aliyun.com/pypi/simple/


COPY . .


CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]