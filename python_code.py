#!/usr/bin/env python3

__version__ = "2.0.0"


import sys
import os
import json
import subprocess
import locale
import ctypes
import locale
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFileDialog, QComboBox, QCheckBox, QTextEdit, QMessageBox,
    QSpacerItem, QSizePolicy, QCompleter
)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt

from datetime import datetime

PREF_FILE = Path.home() / ".winmklink_prefs.json"

LINK_TYPES = {
    "symlink_file": {"zh": "符号链接（文件）", "en": "Symbolic Link (File)"},
    "symlink_dir": {"zh": "符号链接（目录）", "en": "Symbolic Link (Directory)"},
    "hardlink_file": {"zh": "硬链接（文件）", "en": "Hard Link (File)"},
    "junction": {"zh": "目录联接（Junction）", "en": "Junction (Directory)"},
}

LANG_TEXTS = {
    "en": {
        "title": "Winmklink GUI Tool",
        "target": "Target Path:",
        "link": "Link Path:",
        "link_type": "Link Type:",
        "tip_target": "Select the existing target file or directory",
        "tip_link": "Choose where to create the link (will suggest target's name)",
        "choose": "Browse",
        "lang": "Language:",
        "create": "Create Link",
        "output": "Output:",
        "cmd_preview": "Command Preview:",
        "admin_run": "Restart as Admin",
        "need_admin_to_create": "Creating links requires administrator privileges. Restart as admin?",
        "status_admin": "Running as Administrator",
        "status_not_admin": "Not running as Administrator",
        "batch_display": "Batch link all files in the selected directory",
        "display_theme": "theme:",
        "theme_a": "Auto",
        "theme_l": "Day",
        "theme_n": "Night",
    },
    "zh": {
        "title": "Win链接工具GUI",
        "target": "目标路径：",
        "link": "链接路径：",
        "link_type": "链接类型：",
        "tip_link": "选择链接位置（默认建议目标名称）",
        "tip_target": "选择已存在的目标文件或目录",
        "choose": "浏览",
        "lang": "语言：",
        "create": "创建链接",
        "output": "输出：",
        "cmd_preview": "命令预览：",
        "admin_run": "以管理员重启",
        "need_admin_to_create": "创建链接需要管理员权限。要现在以管理员重启吗？",
        "status_admin": "已使用管理员权限运行",
        "status_not_admin": "未使用管理员权限运行",
        "batch_display": "批量链接所选目录下的所有文件",
        "display_theme": "主题:",
        "theme_a": "自动",
        "theme_l": "白天",
        "theme_n": "夜间",
    }
}


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def restart_as_admin():
    python = sys.executable
    script = os.path.abspath(sys.argv[0])
    params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
    cmd = f'"{script}" {params}'.strip()
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", python, cmd, None, 1)
        return isinstance(rc, int) and rc > 32
    except Exception:
        return False

def is_daytime():
    hour = datetime.now().hour
    return 6 <= hour < 18


class WinMkLinkQt(QWidget):
    
    DAY_STYLE = """
    QWidget {
      background-color: #f0f0f0;
      color: #000000;
    }
    QLineEdit, QTextEdit {
      background-color: #ffffff;
      color: #000000;
    }
    QComboBox, QCheckBox, QPushButton {
      background-color: #e0e0e0;
      color: #000000;
    }
    """

    NIGHT_STYLE = """
    QWidget {
      background-color: #2b2b2b;
      color: #ffffff;
    }
    QLineEdit, QTextEdit {
      background-color: #3c3c3c;
      color: #ffffff;
    }
    QComboBox, QCheckBox, QPushButton {
      background-color: #444444;
      color: #ffffff;
    }
    """

    def apply_theme(self, theme=None):
      if theme == "day":
          self.setStyleSheet(self.DAY_STYLE)
      elif theme == "night":
          self.setStyleSheet(self.NIGHT_STYLE)
      else:  # 自动模式
          if is_daytime():
              self.setStyleSheet(self.DAY_STYLE)
          else:
              self.setStyleSheet(self.NIGHT_STYLE)

    def on_theme_change(self, text):
      if text == "自动":
          self.apply_theme()
      elif text == "白天":
          self.apply_theme("day")
      else:
          self.apply_theme("night")

    def detect_system_lang():
      lang_code, _ = locale.getdefaultlocale()  # 例如 'zh_CN' 或 'en_US'
      if lang_code and lang_code.startswith('zh'):
          return 'zh'
      else:
          return 'en'
          self.lang = self.load_lang_pref() or detect_system_lang()
          lang_code, _ = locale.getdefaultlocale() or ('en_US', None)


    def __init__(self):
        super().__init__()
        self.lang = self.load_lang_pref()
        if self.lang not in LANG_TEXTS:
            self.lang = 'zh'
        self.texts = LANG_TEXTS[self.lang]
        self.setWindowTitle(self.texts['title'])
        self.setMinimumSize(760, 520)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            self.texts["theme_a"],
            self.texts["theme_l"],
            self.texts["theme_n"]
        ])
        self.theme_combo.setCurrentIndex(0)
        self.theme_combo.currentTextChanged.connect(self.on_theme_change)

        self.target = QLineEdit()
        self.link = QLineEdit()

        self.type_combo = QComboBox()
        self.type_combo.setEditable(True)
        display_vals = self._link_type_list()
        self.type_combo.addItems(display_vals)
        completer = QCompleter(display_vals, self.type_combo)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.type_combo.setCompleter(completer)

        self.batch_check = QCheckBox(self.texts['batch_display'])

        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.preview.setFixedHeight(100)
        self.preview.setFont(QFont('Consolas', 10))

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setFont(QFont('Consolas', 10))

        self.admin_btn = QPushButton(self.texts['admin_run'])
        self.status_label = QLabel('')

        self.init_ui()
        self.update_admin_status()
        self.update_preview()

        self.apply_theme()


    def init_ui(self):
        v = QVBoxLayout()

        # top: language and admin
        top_h = QHBoxLayout()
        lang_label = QLabel(self.texts['lang'])
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(['中文', 'English'])
        self.lang_combo.setCurrentIndex(0 if self.lang == 'zh' else 1)
        self.lang_combo.currentIndexChanged.connect(self.change_lang)
        top_h.addWidget(lang_label)
        top_h.addWidget(self.lang_combo)

        top_h.addWidget(QLabel(self.texts['display_theme']))
        top_h.addWidget(self.theme_combo)

        top_h.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        top_h.addWidget(self.status_label)
        top_h.addWidget(self.admin_btn)
        self.admin_btn.clicked.connect(self.on_admin_button)
        v.addLayout(top_h)

        # target
        t_h = QHBoxLayout()
        t_h.addWidget(QLabel(self.texts['target']))
        t_h.addWidget(self.target)
        self.btn_target = QPushButton(self.texts['choose'])
        self.btn_target.clicked.connect(self.browse_target)
        t_h.addWidget(self.btn_target)
        v.addLayout(t_h)

        # link
        l_h = QHBoxLayout()
        l_h.addWidget(QLabel(self.texts['link']))
        l_h.addWidget(self.link)
        self.btn_link = QPushButton(self.texts['choose'])
        self.btn_link.clicked.connect(self.browse_link)
        l_h.addWidget(self.btn_link)
        v.addLayout(l_h)

        # link type and batch
        type_h = QHBoxLayout()
        type_h.addWidget(QLabel(self.texts['link_type']))
        type_h.addWidget(self.type_combo)
        type_h.addWidget(self.batch_check)
        v.addLayout(type_h)

        # preview
        v.addWidget(QLabel(self.texts['cmd_preview']))
        v.addWidget(self.preview)

        # create button
        btn_h = QHBoxLayout()
        self.create_btn = QPushButton(self.texts['create'])
        self.create_btn.clicked.connect(self.on_create)
        btn_h.addWidget(self.create_btn)
        btn_h.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        v.addLayout(btn_h)

        # output
        v.addWidget(QLabel(self.texts['output']))
        v.addWidget(self.output)

        # signals
        self.target.textChanged.connect(self.update_preview)
        self.link.textChanged.connect(self.update_preview)
        self.type_combo.currentTextChanged.connect(self.on_type_change)
        self.batch_check.stateChanged.connect(self.update_preview)

        self.setLayout(v)

        self.target.setToolTip(self.texts.get('tip_target', ''))
        self.link.setToolTip(self.texts.get('tip_link', ''))
        self.btn_target.setToolTip(self.texts.get('tip_target', ''))
        self.btn_link.setToolTip(self.texts.get('tip_link', ''))

        # vershin
        bottom_h = QHBoxLayout()
        bottom_h.addItem(QSpacerItem(20, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))  # 占位
        self.version_label = QLabel(f"v{__version__}")
        bottom_h.addWidget(self.version_label)
        v.addLayout(bottom_h)



    def _link_type_list(self):
        return [v[self.lang] for v in LINK_TYPES.values()]

    def _link_type_key(self):
        disp = self.type_combo.currentText()
        for k, v in LINK_TYPES.items():
            if v[self.lang] == disp:
                return k
        lower = disp.lower()
        for k, v in LINK_TYPES.items():
            if lower in v['en'].lower() or lower in v['zh']:
                return k
        return 'symlink_file'

    def browse_target(self):
        key = self._link_type_key()
        if self.batch_check.isChecked() or key in ('symlink_dir', 'junction'):
            path = QFileDialog.getExistingDirectory(self, self.texts['target'])
        else:
            path, _ = QFileDialog.getOpenFileName(self, self.texts['target'])
        if path:
            self.target.setText(path)

    def browse_link(self):
        key = self._link_type_key()
        target = self.target.text()
        initial = os.path.dirname(target) if target else os.getcwd()
        if self.batch_check.isChecked() or key in ('symlink_dir', 'junction'):
            path = QFileDialog.getExistingDirectory(self, self.texts['link'], initial)
        else:
            path, _ = QFileDialog.getSaveFileName(self, self.texts['link'], initialDir=initial, initialFilter='')
        if path:
            self.link.setText(path)

    def on_type_change(self, *_):
        key = self._link_type_key()
        if key == 'symlink_file':
            self.batch_check.setEnabled(True)
        else:
            self.batch_check.setEnabled(False)
            self.batch_check.setChecked(False)
        self.update_preview()

    def update_preview(self):
       target = self.target.text()
       link = self.link.text()
       key = self._link_type_key()
       if not target or not link:
           self.preview.setPlainText('')
           return

       if self.batch_check.isChecked() and os.path.isdir(target):
           all_files = []
           for root, dirs, files in os.walk(target):
               for f in files:
                   all_files.append(os.path.join(root, f))
           if all_files:
               example = all_files[0]
               try:
                   rel = os.path.relpath(example, start=target)
               except Exception:
                   rel = os.path.basename(example)
               link_target = os.path.normpath(os.path.join(link, rel))
               cmd = self._build_cmd(link_target, example, key)
               text = (
                   f"(示例) {cmd}\n\n"
                   f"批量模式，共 {len(all_files)} 个文件，将基于目标目录结构创建链接。"
               )
           else:
               text = ''
       else:
           cmd = self._build_cmd(link, target, key)
           text = cmd

       self.preview.setPlainText(text)


    def _build_cmd(self, link_path, target_path, key):
        parts = ['mklink']
        if key == 'symlink_dir':
            parts.append('/D')
        elif key == 'junction':
            parts.append('/J')
        elif key == 'hardlink_file':
            parts.append('/H')
        parts.append(f'"{link_path}"')
        parts.append(f'"{target_path}"')
        return ' '.join(parts)

    def on_create(self):
        if not is_admin():
            reply = QMessageBox.question(self, self.texts['title'], self.texts['need_admin_to_create'], QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                ok = restart_as_admin()
                if ok:
                    QApplication.quit()
                    return
                else:
                    QMessageBox.critical(self, self.texts['title'], 'Failed to restart as admin')
            return
        # proceed
        self.execute_links()

    def execute_links(self):
        target = self.target.text()
        link_dir = self.link.text()
        key = self._link_type_key()
        if not target or not link_dir:
            QMessageBox.warning(self, self.texts['title'], 'Please select target and link directory.')
            return
        files = []
        if self.batch_check.isChecked() and os.path.isdir(target):
            for root, dirs, filenames in os.walk(target):
                for f in filenames:
                    files.append(os.path.join(root, f))
        else:
            files = [target]

        enc = locale.getpreferredencoding(False)
        self.output.clear()
        for file in files:
            link_path = link_dir if not self.batch_check.isChecked() else os.path.join(link_dir, os.path.relpath(file, start=target))
            link_path = os.path.normpath(link_path)
            cmd = self._build_cmd(link_path, file, key)
            full = f'cmd.exe /c {cmd}'
            try:
                r = subprocess.run(full, shell=True, capture_output=True, text=True, encoding=enc, errors='ignore')
                if r.stdout:
                    self.output.append(r.stdout)
                if r.stderr:
                    self.output.append(r.stderr)
            except Exception as e:
                self.output.append(str(e))
        self.output.append('Done.')

    def on_admin_button(self):
        if is_admin():
            QMessageBox.information(self, self.texts['title'], self.texts['status_admin'])
            return
        ok = restart_as_admin()
        if ok:
            QApplication.quit()
        else:
            QMessageBox.critical(self, self.texts['title'], 'Failed to restart as admin')

    def update_admin_status(self):
        if is_admin():
            self.status_label.setText(self.texts['status_admin'])
        else:
            self.status_label.setText(self.texts['status_not_admin'])

    def change_lang(self, idx):
        self.lang = 'zh' if idx == 0 else 'en'
        self.save_lang_pref(self.lang)
        # restart to apply
        python = sys.executable
        os.execl(python, python, *sys.argv)
        # 更新文本和 tooltip
        self.texts = LANG_TEXTS[self.lang]
        self.target.setToolTip(self.texts.get('tip_target', ''))
        self.link.setToolTip(self.texts.get('tip_link', ''))
        self.btn_target.setToolTip(self.texts.get('tip_target', ''))
        self.btn_link.setToolTip(self.texts.get('tip_link', ''))

    def load_lang_pref(self):
        if PREF_FILE.exists():
            try:
                with open(PREF_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('lang', 'zh')
            except Exception:
                return 'zh'
        return 'zh'

    def save_lang_pref(self, lang):
        try:
            with open(PREF_FILE, 'w', encoding='utf-8') as f:
                json.dump({'lang': lang}, f)
        except Exception:
            pass


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WinMkLinkQt()
    window.show()
    sys.exit(app.exec())
