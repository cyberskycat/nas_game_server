FROM python:3.10-slim

# 安装 Docker CLI 客户端
RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian \
      $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null \
    && apt-get update && apt-get install -y docker-ce-cli \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制 Agent 代码和 UI 资源
COPY edge_agent /app/edge_agent

# 暴露 UI 端口
EXPOSE 8001

# 设置环境变量默认值
ENV CENTER_URL=http://localhost:8123

# 以模块方式启动 Agent，支持相对导入
CMD ["python", "-u", "-m", "edge_agent.agent"]
