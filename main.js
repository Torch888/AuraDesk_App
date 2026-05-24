const { app, BrowserWindow, screen } = require('electron');
const path = require('path');

function createWindow() {
  // 获取屏幕可用区域尺寸，让数字人默认显示在右下角
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  const win = new BrowserWindow({
    width: 300,
    height: 400,
    x: width - 320, // 距离右侧 20px
    y: height - 420, // 距离底部 20px
    transparent: true, // 核心：背景透明
    frame: false, // 核心：无边框
    alwaysOnTop: true, // 核心：永远置顶悬浮
    skipTaskbar: true, // 不在 Dock / 任务栏显示
    resizable: false, // 禁止拉伸
    hasShadow: false,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  // 加载界面
  win.loadFile(path.join(__dirname, 'index.html'));

  // 让窗口鼠标可以穿透，可按需开启
  // win.setIgnoreMouseEvents(true, { forward: true });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
