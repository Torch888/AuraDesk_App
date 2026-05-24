"""系统通知模块 - 支持 Windows Toast / macOS 通知 / 控制台输出"""
from __future__ import annotations

import json
import platform
import subprocess

from packages.shared.models import NotificationMessage


class Notifier:
    def __init__(self):
        self._os = platform.system()

    def send(self, msg: NotificationMessage):
        """发送系统通知"""
        print(f"\n{'='*50}")
        print(f"  🔔 [{msg.category.upper()}] {msg.title}")
        print(f"  📝 {msg.body}")
        if msg.action_url:
            print(f"  🔗 {msg.action_url}")
        print(f"{'='*50}\n")

        # Windows Toast 通知
        if self._os == "Windows":
            self._send_windows_toast(msg)
        # macOS 通知
        elif self._os == "Darwin":
            self._send_macos_notification(msg)

    def _send_windows_toast(self, msg: NotificationMessage):
        """Windows 10/11 Toast 通知 (PowerShell)"""
        try:
            ps_script = f'''
            [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
            $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
            $textNodes = $template.GetElementsByTagName("text")
            $textNodes.Item(0).AppendChild($template.CreateTextNode("{msg.title}")) > $null
            $textNodes.Item(1).AppendChild($template.CreateTextNode("{msg.body}")) > $null
            $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
            [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("AuraDesk").Show($toast)
            '''
            subprocess.run(["powershell", "-Command", ps_script], capture_output=True, timeout=5)
        except Exception as e:
            print(f"  ⚠️ Windows Toast 发送失败: {e}")

    def _send_macos_notification(self, msg: NotificationMessage):
        """macOS 系统通知"""
        try:
            subprocess.run([
                "osascript", "-e",
                f'display notification "{msg.body}" with title "{msg.title}" sound name "Glass"'
            ], capture_output=True, timeout=5)
        except Exception as e:
            print(f"  ⚠️ macOS 通知发送失败: {e}")


notifier = Notifier()