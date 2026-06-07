#!/bin/bash

# AuraDesk 启动脚本

echo "================================"
echo "  AuraDesk - AI 桌面生活助手"
echo "================================"
echo ""

# 检查 Node.js
if ! command -v node &> /dev/null; then
    echo "错误: 未安装 Node.js"
    echo "请访问 https://nodejs.org 下载安装"
    exit 1
fi

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "首次运行，正在安装依赖..."
    npm install
    echo ""
fi

echo "选择启动模式："
echo "  1) 仅桌面助手（推荐）"
echo "  2) 桌面助手 + 云端后端"
echo ""
read -p "请输入选项 [1]: " choice

case $choice in
    2)
        echo ""
        echo "启动云端后端..."
        npm run cloud &
        CLOUD_PID=$!
        sleep 2
        
        echo "启动桌面助手..."
        AURADESK_CLOUD_URL=http://127.0.0.1:8787 AURADESK_CLOUD_TOKEN=*** npm start
        
        # 退出时关闭云端后端
        kill $CLOUD_PID 2>/dev/null
        ;;
    *)
        echo ""
        echo "启动桌面助手..."
        npm start
        ;;
esac
