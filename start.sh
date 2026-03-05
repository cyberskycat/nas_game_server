#!/bin/bash

# 确保在项目根目录运行
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"
#清理
./cleanup.sh
# 构建前端
cd frontend
npm run build
cd ..
docker-compose up -d --build