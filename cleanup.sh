#!/bin/bash

# 确保在项目根目录运行
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo "Stopping and cleaning up all game-related resources..."

# 1. 如果存在 docker-compose 启动的服务，也一并清理
if [ -f "docker-compose.yml" ]; then
    echo "Stopping docker-compose services..."
    docker-compose down --remove-orphans
fi

# 2. 停止并强制删除所有名称匹配 game-* 的容器（包含游戏实例）
CONTAINERS=$(docker ps -a --filter "name=game-" -q)
if [ -n "$CONTAINERS" ]; then
    echo "Stopping remaining containers: $CONTAINERS"
    docker rm -f $CONTAINERS
fi

# 3. 杀掉可能正在运行的本地进程 (针对遗留进程)
echo "Killing local Python processes..."
pkill -9 -f "edge_agent/agent.py" || true
pkill -9 -f "center.app.main:app" || true

# 4. 清理数据目录 (保留 .db 文件如果需要持久化测试，但 cleanup.sh 默认是全清)
echo "Cleaning up data and logs..."
rm -rf center_data agent1_data agent2_data
rm -rf /tmp/edge_agent_data
rm -rf /tmp/game_saves
rm -f center.log

echo "Cleanup complete. System is fresh."
