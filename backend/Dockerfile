FROM python:3.11


WORKDIR /app


COPY requirements.txt .
# 安装CPU版本PyTorch
RUN pip install --no-cache-dir \
    torch==2.13.0 \
    --index-url https://download.pytorch.org/whl/cpu


# 安装其他依赖
RUN pip install --no-cache-dir -r requirements.txt


COPY . .


COPY . .


CMD ["uvicorn","main:app","--host","0.0.0.0","--port","8000"]