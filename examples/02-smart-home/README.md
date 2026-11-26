# 实战二配套代码：智能家居联动（开门迎宾）

对应教程：[实战二：智能家居联动](../../docs/zh-CN/project-02-smart-home.md)。

`door_welcome.py` 是完整可运行的常驻程序，把门窗传感器、EBO 机器人和米家设备串成一条自动化流程。

## 环境

- Python 3.11+
- 包管理：uv
- 操作系统：Windows / macOS / Linux
- 米家账号、门窗传感器、智能灯泡、中枢网关
- 已建图的 EBO 机器人，与运行脚本的电脑在同一局域网

依赖版本见 `requirements.txt`，是项目实测可用的下限。

## 运行

```bash
# 方式一：uv 直接运行（按需拉取依赖）
uv run --python 3.11 door_welcome.py

# 方式二：先建虚拟环境
uv venv --python 3.11 .venv
source .venv/bin/activate        # Windows 下为 .venv\Scripts\activate
pip install -r requirements.txt
python door_welcome.py
```

`run.sh` 里是同样的命令。

首次使用需扫码登录米家账号，凭证保存在 `~/.config/mijia-api`，之后自动刷新。EBO 的令牌建议通过环境变量 `EBO_TOKEN` 注入。

## 停止

- Ctrl+C 或关闭窗口（推荐）
- 删除同目录的 `door_welcome.run` 标志文件，程序下个轮询周期会退出

退出时脚本会清理现场：停止音乐、完全停止移动（含跟随）、关灯。

## 改配置

打开文件顶部的配置区，可修改：设备名、导航地点、欢迎语文案、音乐风格、跟随模式与目标、轮询间隔与冷却时间。

地点名必须与地图里的名字完全一致，否则导航失败。换环境后先调用 `robot_list_locations` 核对。
