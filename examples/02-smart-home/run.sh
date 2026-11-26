# 方式一：uv 直接运行（按需拉取依赖，推荐）
uv run --python 3.11 door_welcome.py

# 方式二：先建虚拟环境再装依赖
uv venv --python 3.11 .venv
source .venv/bin/activate        # Windows 下为 .venv\Scripts\activate
pip install -r requirements.txt
python door_welcome.py
