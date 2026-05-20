# Windows-mklink-GUI
[English](./README_EN.md) [中文](./README.md)

A GUI implementation of the mklink command in cmd on the Windows platform(It's a bit of a hassle to type commands...)

Implementing linked files in Windows using Python
Currently, soft links require administrator privileges to implement, which Python cannot handle. If you need soft links, we recommend running the Python script directly as an administrator.

## run

Install dependencies on Windows: pip install ttkbootstrap

Run: python main.py

```bash
pip install -r requirements.txt
python main.py
```

If you need a symbolic link, run as an administrator, or use the “Run as administrator” button to execute the command in a new window as an administrator.
