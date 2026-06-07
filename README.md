# AuraDesk - AI 桌面生活助手

## 简介

AuraDesk 是一款专为海外用户打造的 AI 桌面生活助手，具备以下核心功能：

- **AI 智能助手**：集成 DeepSeek V3，支持自然语言交互
- **语音控制**：支持 50+ 种语言的语音输入和播报
- **用药提醒**：慢病患者预设模板（糖尿病、高血压等）
- **多语言支持**：切换语言后，界面、语音、内容同步切换
- **云端同步**：多设备数据同步

## 快速开始

### 1. 安装依赖

```bash
npm install
```

### 2. 启动应用

**方式一：直接启动桌面助手**
```bash
npm start
```

**方式二：启动云端后端 + 桌面助手**
```bash
# 终端 1：启动云端后端
npm run cloud

# 终端 2：启动桌面助手（连接云端）
AURADESK_CLOUD_URL=http://127.0.0.1:8787 AURADESK_CLOUD_TOKEN=dev-token npm start
```

### 3. 配置 AI 助手

1. 点击小精灵 → 点击 ⚙ 设置
2. 滚动到底部 → 点击「AI 助手」
3. 点击 🔑 按钮设置 DeepSeek API Key
4. 在 https://platform.deepseek.com 获取 API Key

## 功能说明

### 桌面小精灵
- 悬浮在屏幕右下角
- 支持拖拽移动
- 双击切换主题（奶油小熊/粉兔精灵/橘猫助手/云朵团子）
- 点击打开设置面板

### 语音控制
- 点击 🎤 按钮开始语音输入
- 支持 50+ 种语言识别
- 切换语音区域后，识别语言自动切换

### 用药提醒
- 预设糖尿病、高血压、高血脂、甲状腺、心脏病模板
- 一键添加常用药物提醒
- 支持漏服升级通知

### 多语言支持
支持的语言包括：
- 东亚：中文、日语、韩语
- 东南亚：泰语、越南语、印尼语、马来语等
- 南亚：印地语、乌尔都语、孟加拉语等
- 欧洲：英语、法语、德语、西班牙语、俄语等
- 非洲：斯瓦希里语、豪萨语等
- 美洲：英语、西班牙语、葡萄牙语

### AI 助手
- 集成 DeepSeek V3 大模型
- 支持自然语言创建提醒
- 可管理用药提醒、切换语言等

## 文件结构

```
AuraDesk_Release/
├── index.html          # 主界面（Electron 渲染进程）
├── main.js             # Electron 主进程
├── cloud-server.js     # 云端后端服务
├── mobile.html         # 手机端界面
├── package.json        # 项目配置
└── README.md           # 本文件
```

## 技术栈

- **前端**：HTML5 + CSS3 + JavaScript
- **桌面框架**：Electron
- **后端**：Node.js
- **AI 模型**：DeepSeek V3
- **语音**：Web Speech API
- **数据存储**：JSON 文件

## 环境要求

- Node.js 16+
- npm 8+
- macOS / Windows / Linux

## 常见问题

### Q: 小精灵不显示？
A: 检查是否有其他 Electron 进程占用，运行 `pkill -f electron` 后重试。

### Q: AI 助手不工作？
A: 需要设置 DeepSeek API Key，点击 🔑 按钮输入。

### Q: 语音识别不准确？
A: 切换到对应语言的语音区域，识别会更准确。

### Q: 如何自定义提醒？
A: 对 AI 助手说「帮我创建一个明天下午3点开会的提醒」。

## 许可证

MIT License
