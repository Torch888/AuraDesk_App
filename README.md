# AuraDesk 数字人视觉与语音模块

这是 AuraDesk 项目中“数字人视觉与语音模块”的整理版，可直接上传到 GitHub 仓库 `AuraDesk_App`。

## 包含文件

- `index.html`：数字人界面、形象、动画、状态切换、语音设置、互动文案库
- `main.js`：Electron 悬浮窗口、透明置顶、拖动窗口 IPC
- `package.json`：项目启动配置
- `package-lock.json`：依赖锁定文件
- `.gitignore`：忽略 node_modules 等本地文件

## 已完成功能

- Q 版小精灵/小熊助手形象
- 双击切换形象：奶油小熊、粉兔精灵、橘猫助手、云朵团子
- 鼠标悬停显示右上角控制按钮
- 默认隐藏下方功能区，点击设置图标后显示
- 支持拖动数字人移动窗口
- 支持放大、缩小、收起、打开界面
- 支持语音开关、音色选择、语速、音调、音量、试听
- 支持说话动画、眨眼、漂浮、提醒、思考、睡眠状态
- 增加问候、会议、抢票、休息、夸奖、鼓励文案库

## 运行方式

```bash
npm install
npm start
```

## 给团队使用的公共接口

在页面中已暴露：

```js
window.AuraDeskAvatar
```

可调用：

```js
AuraDeskAvatar.speakAndShow('10分钟后有会议哦，记得准备一下。', {
  state: 'alert',
  type: 'meeting'
});

AuraDeskAvatar.setAvatarState('happy');
AuraDeskAvatar.nextAvatarTheme();
AuraDeskAvatar.changeAvatarSize(0.06);
```

## 建议上传到 GitHub 的文件

上传整个文件夹里的内容即可，不要上传 `node_modules`。
