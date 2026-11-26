# -*- coding: utf-8 -*-
"""
door_welcome.py - 开门迎宾自动化（独立程序版）

流程：
  ① 门窗传感器检测「关门→开门」边沿
  ② EBO 导航到客厅
  ③ 检测人：先查 robot_status，无人则短暂等待后用 robot_search_360 再查；仍无人则跳过
  ④ 识别到人 → TTS「{名字}，欢迎回家，为您打开客厅的灯」
     （若只识别到人但 MCP 未返回人名 → TTS「欢迎回家，为您打开客厅的灯」）
  ⑤ 开灯
  ⑥ 启动人跟随（robot_follow）
  ⑦ TTS「为您播放您最喜欢的音乐」+ 播放音乐（风格类别），与跟随并行

运行方式（在 mcp-mijia-master 目录下）：
    uv run --python 3.11 door_welcome.py

停止方式：
    方式1：直接关闭窗口 / Ctrl+C（推荐）
    方式2：删除同目录 door_welcome.run 标志文件，脚本下个轮询周期退出
"""
import asyncio
import logging
import os
import re
import sys
import time

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ==================== 配置区 ====================
EBO_URL = os.environ.get('EBO_URL', '<EBO_MCP_ENDPOINT>')
EBO_TOKEN = os.environ.get('EBO_TOKEN', 'ebo_mcp_71P2lCoji5ewnOvAbdarjsbdeR07XI0L')
DOOR_SENSOR = 'Xiaomi Door and Window Sensor 3'   # 米家门窗传感器名称
LIGHT_NAME = '灯泡'                                # 米家灯泡名称
DOOR_LOCATION = '客厅'                             # EBO 地图中的导航目标位置名
GREETING_TPL = '{name}，欢迎回家，为您打开客厅的灯'  # ④ 识别到具体人名时的欢迎语
GREETING_NO_NAME = '欢迎回家，为您打开客厅的灯'      # ④ 只识别到人但未返回人名时的欢迎语
MUSIC_NOTICE = '为您播放您最喜欢的音乐'              # ⑦ 播放音乐前的播报
MUSIC_STYLE = '轻音乐'                              # ⑦ 音乐风格类别（robot_play_music 的 text 参数）
FOLLOW_MODE = 0       # ⑥ 跟随模式：0=跟随, 1=锁定
FOLLOW_TARGET = 4     # ⑥ 跟随目标：4=人, 3=宠物

POLL_INTERVAL = 3     # 传感器轮询间隔（秒）
COOLDOWN = 30         # 触发后的冷却时间（秒）
STATUS_POLL = 5       # 导航状态轮询间隔（秒）
NAV_TIMEOUT = 120     # 导航最长等待（秒），超时也继续
LIGHT_RETRIES = 3     # 开灯重试次数（BLE Mesh 灯泡偶发"设备离线"）
LIGHT_RETRY_WAIT = 2  # 开灯重试间隔（秒）
PERSON_WAIT = 10      # ③ 到门口后无人时的等待再检测时长（秒）
PERSON_MAX_WAIT = 40  # ③ 等待检测人的最长总时间（秒）
TTS_CHARS_PER_SEC = 4.0  # TTS 播报速度估算（字/秒），保守值
TTS_MIN_WAIT = 2.0       # TTS 最短等待（秒）
TTS_BUFFER = 1.5         # TTS 播完后的额外缓冲（秒）

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FLAG_FILE = os.path.join(BASE_DIR, 'door_welcome.run')
LOG_FILE = os.path.join(BASE_DIR, 'door_welcome.log')
# ===============================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
    ],
)
log = logging.getLogger('door_welcome')


class EboClient:
    """EBO MCP HTTP 客户端封装：会话管理 + 工具调用 + 断线重连"""

    def __init__(self, url, token):
        self.url = url
        self.headers = {'Authorization': f'Bearer {token}'}
        self._http = None
        self._streams_ctx = None
        self._session_ctx = None
        self._session = None

    async def __aenter__(self):
        await self._connect()
        return self

    async def __aexit__(self, *exc):
        await self._teardown()

    async def _connect(self):
        from mcp.client.streamable_http import streamable_http_client, create_mcp_http_client
        from mcp import ClientSession

        self._http = create_mcp_http_client(headers=self.headers)
        self._streams_ctx = streamable_http_client(self.url, http_client=self._http)
        read, write = await self._streams_ctx.__aenter__()
        # ClientSession 必须用 async with 进入（启动 dispatcher）
        self._session_ctx = ClientSession(read, write)
        self._session = await self._session_ctx.__aenter__()
        await self._session.initialize()
        log.info('EBO MCP 已连接')

    async def _teardown(self):
        try:
            if self._session_ctx is not None:
                await self._session_ctx.__aexit__(None, None, None)
        except Exception as e:
            log.debug(f'session 退出异常: {e}')
        try:
            if self._streams_ctx is not None:
                await self._streams_ctx.__aexit__(None, None, None)
        except Exception as e:
            log.debug(f'streams 退出异常: {e}')
        if self._http is not None:
            try:
                await self._http.aclose()
            except Exception:
                pass
        self._http = None
        self._streams_ctx = None
        self._session_ctx = None
        self._session = None

    async def call(self, tool, args=None, retries=1):
        """调用 EBO 工具；失败时重连并重试"""
        for attempt in range(retries + 1):
            try:
                result = await self._session.call_tool(tool, args or {})
                texts = [c.text for c in result.content if getattr(c, 'text', None)]
                return ' | '.join(texts) if texts else 'OK'
            except Exception as e:
                log.warning(f'调用 {tool} 失败(第{attempt + 1}次): {e}')
                if attempt < retries:
                    await self._reconnect()
        return None

    async def _reconnect(self):
        log.info('尝试重连 EBO MCP...')
        await self._teardown()
        await self._connect()


async def wait_nav_done(ebo, timeout=NAV_TIMEOUT):
    """等待导航任务结束，每10秒查询一次状态，直到设备任务变为空闲。"""
    waited = 0
    while waited < timeout:
        await asyncio.sleep(STATUS_POLL)
        waited += STATUS_POLL
        text = await ebo.call('robot_status', {}) or ''
        if '设备任务：空闲' in text:
            log.info(f'导航完成（已等{waited}s）')
            return True
        log.info(f'导航进行中（已等{waited}s）')
    log.warning(f'导航等待超时（{timeout}s），继续播报')
    return False


def normalize_name_for_tts(name):
    """
    把人名规范化为对中文 TTS 友好的形式。
    设备返回的人名是全大写（如 DAVID），中文 TTS 引擎常把全大写英文串当作
    缩写逐字母念（D-A-V-I-D）。转成首字母大写（David）后一般按正常单词念。
    仅处理纯 ASCII 英文（可含空格/点/连字符/撇号），中文名等保持原样。
    """
    if not name:
        return name
    if re.fullmatch(r"[A-Za-z][A-Za-z\s.'-]*", name):
        return name.title()
    return name


def parse_person(text):
    """
    从 robot_status 文本解析检测到的人。
    返回 (人名 or None, 人数)。

    实际返回样例（无人）：
      Users currently detected in the camera view (...): none
      当前检测到人数：0
    有人时该行会列出名字（名字后跟坐标，可能是 JSON 或圆括号）：
      ...: 张三 (0.42, 0.31)
      ...: DAVID {"leftTopX":0.382812, "leftTopY":0.1, ...}
    多人时以逗号分隔，取第一个人名。
    """
    if not text:
        return None, 0

    count = 0
    name = None

    # 人数：优先中文行
    m = re.search(r'当前检测到人数[：:]\s*(\d+)', text)
    if m:
        count = int(m.group(1))

    # 名字：取 "Users currently detected ...:" 之后的内容
    m = re.search(r'Users currently detected[^\n]*?[：:]\s*(.+)', text)
    if m:
        val = m.group(1).strip()
        if val and val.lower() != 'none':
            # 先去掉坐标部分——设备返回两种格式：
            #   圆括号: "张三 (0.42, 0.31)"
            #   JSON:   'DAVID {"leftTopX":0.382812, "leftTopY":0.1, ...}'
            # 必须先于逗号分割处理，否则 JSON 内的逗号会把名字切断。
            name = re.sub(r'\s*\{.*?\}\s*', '', val)   # 去 JSON 坐标对象
            name = re.sub(r'\s*\(.*?\)\s*', '', name)  # 去圆括号坐标
            name = name.strip()
            # 多人时用逗号/分号分隔，取第一个
            name = re.split(r'[,，;；]', name)[0].strip()
            if name.lower() == 'none' or not name:
                name = None
            if count == 0:
                count = 1
    return name, count


async def detect_person(ebo):
    """
    ③ 检测目标地点是否有人。策略：
      1) 先查 robot_status
      2) 无人则等待 PERSON_WAIT 秒再查一次
      3) 仍无人则调用 robot_search_360 主动环顾（阻塞调用）
      返回：
        - None：完全没检测到人 → 跳过迎宾
        - 人名字符串：识别到具体人名 → 播报带名字版本
        - 空字符串 ''：检测到人但未识别到人名 → 播报不带名字版本
    """
    # 第一次：status
    text = await ebo.call('robot_status', {}) or ''
    name, count = parse_person(text)
    log.info(f'③ 首次检测人: 人数={count}, 名字={name!r}')
    if name is not None or count > 0:
        return name or ''

    # 第二次：等待后再查 status
    log.info(f'③ 无人，等待 {PERSON_WAIT}s 后再检测')
    await asyncio.sleep(PERSON_WAIT)
    text = await ebo.call('robot_status', {}) or ''
    name, count = parse_person(text)
    log.info(f'③ 二次检测人: 人数={count}, 名字={name!r}')
    if name is not None or count > 0:
        return name or ''

    # 第三次：360° 环顾主动搜索人
    log.info('③ 仍无人，调用 robot_search_360 主动环顾')
    r = await ebo.call('robot_search_360', {'objId': '1', 'lang': 'zh-CN'})
    log.info(f'③ search_360 结果: {r}')
    if r:
        text = await ebo.call('robot_status', {}) or ''
        name, count = parse_person(text)
        log.info(f'③ 环顾后检测: 人数={count}, 名字={name!r}')
        if name is not None or count > 0:
            return name or ''
    return None


async def speak_and_wait(ebo, text, lang='zh-CN'):
    """
    播报并等待完整播完后再返回。

    robot_speak 只返回"消息已发送"，且 robot_status 在播报期间无任何字段
    反映播放状态（实测设备任务仍"空闲"、音乐"已停止"，且有约20s缓存），
    因此无法靠状态轮询判断播完。这里按字符数保守估算时长并留缓冲：
        等待 = max(最短等待, 字数/语速) + 缓冲
    中文按 4 字/秒估算，句末停顿也已计入缓冲。
    """
    r = await ebo.call('robot_speak', {'text': text, 'lang': lang})
    # 估算时长：只统计有效字符（去空格/标点影响较小，直接用 len 偏保守）
    est = max(TTS_MIN_WAIT, len(text) / TTS_CHARS_PER_SEC) + TTS_BUFFER
    log.info(f'播报「{text}」，预计播放 {est:.1f}s，等待其播完: {r}')
    await asyncio.sleep(est)
    return r


async def welcome_flow(ebo, light, api):
    """
    迎宾动作（按用户最新定义）：
      ① 检测开门边沿（由 main 循环负责）
      ② 导航到客厅
      ③ 检测人（无人则短暂等待 + 360°环顾再查，仍无人则跳过）
      ④ TTS「{名字}，欢迎回家，为您打开客厅的灯」
      ⑤ 开灯
      ⑥ 启动人跟随
      ⑦ TTS「为您播放您最喜欢的音乐」+ 播放音乐（与跟随并行）
    """
    log.info('--- 迎宾流程开始 ---')

    # ② 导航到客厅
    r = await ebo.call('robot_navigate', {'locationName': DOOR_LOCATION, 'lang': 'zh-CN'})
    log.info(f'② 导航到「{DOOR_LOCATION}」: {r}')
    await wait_nav_done(ebo)

    # ③ 检测人
    name = await detect_person(ebo)
    if name is None:
        log.info('--- 目标地点未检测到人，跳过迎宾流程 ---')
        return False

    # ④ 识别到人 → 播报欢迎语（必须等完整播完，再开灯/跟随）
    #    有具体人名就带上；只识别到人但 MCP 未返回人名则不带人名
    if name:
        spoken_name = normalize_name_for_tts(name)
        greeting = GREETING_TPL.format(name=spoken_name)
        if spoken_name != name:
            log.info(f'④ 人名 TTS 规范化: {name} -> {spoken_name}（避免逐字母念）')
    else:
        greeting = GREETING_NO_NAME
    await speak_and_wait(ebo, greeting)

    # ⑤ 开灯（BLE Mesh 灯泡经中枢网关下发，偶发"设备离线"，重试可成功）
    light_ok = False
    for attempt in range(1, LIGHT_RETRIES + 1):
        try:
            light.set('on', True)
            log.info(f'⑤ 开灯「{LIGHT_NAME}」: 成功（第{attempt}次尝试）')
            light_ok = True
            break
        except Exception as e:
            log.warning(f'⑤ 开灯失败（第{attempt}/{LIGHT_RETRIES}次）: {e}')
            if attempt < LIGHT_RETRIES:
                await asyncio.sleep(LIGHT_RETRY_WAIT)
    if not light_ok:
        log.warning(f'⑤ 开灯「{LIGHT_NAME}」: {LIGHT_RETRIES}次尝试均失败，跳过')

    # ⑥ 启动人跟随（此时欢迎语已完整播完）
    r = await ebo.call(
        'robot_follow',
        {'mode': FOLLOW_MODE, 'trackTarget': FOLLOW_TARGET, 'lang': 'zh-CN'},
    )
    log.info(f'⑥ 启动人跟随(mode={FOLLOW_MODE}, target={FOLLOW_TARGET}): {r}')

    # ⑦ 播报 + 播放音乐：先等音乐播报完整播完，再放音乐（音乐与跟随并行）
    await speak_and_wait(ebo, MUSIC_NOTICE)
    r = await ebo.call('robot_play_music', {'text': MUSIC_STYLE, 'lang': 'zh-CN'})
    log.info(f'⑦ 播放音乐（风格「{MUSIC_STYLE}」）: {r}')

    log.info(f'--- 迎宾流程结束（跟随+音乐持续中），冷却 {COOLDOWN} 秒 ---')
    return True


async def cleanup_scene(ebo, light):
    """
    程序停止时同步清理现场：停音乐、停跟随（完全停止）、关灯。
    迎宾结束后跟随/音乐/灯会持续，退出时统一清掉，避免遗留状态。
    """
    log.info('--- 停止程序，清理现场 ---')
    try:
        r = await ebo.call('robot_music_control', {'controlType': 4, 'lang': 'zh-CN'})
        log.info(f'清理-停止音乐: {r}')
    except Exception as e:
        log.warning(f'清理-停止音乐失败: {e}')
    try:
        r = await ebo.call('robot_move', {'moveId': 5, 'lang': 'zh-CN'})
        log.info(f'清理-完全停止(含跟随): {r}')
    except Exception as e:
        log.warning(f'清理-停止跟随失败: {e}')
    try:
        light.set('on', False)
        log.info('清理-关灯: 成功')
    except Exception as e:
        log.warning(f'清理-关灯失败: {e}')
    log.info('--- 现场清理完成 ---')


async def main():
    # 1. 创建标志文件
    with open(FLAG_FILE, 'w', encoding='utf-8') as f:
        f.write('running')

    # 2. 登录米家
    from mijiaAPI import mijiaAPI, mijiaDevice, LoginError
    try:
        api = mijiaAPI()          # 默认认证路径 ~/.config/mijia-api
        api.login()
    except LoginError as e:
        log.error(f'米家登录失败: {e}。请先运行 mijia MCP 完成扫码登录。')
        return
    door = mijiaDevice(api, dev_name=DOOR_SENSOR)
    light = mijiaDevice(api, dev_name=LIGHT_NAME)
    log.info(f'米家已登录，传感器「{DOOR_SENSOR}」，灯泡「{LIGHT_NAME}」')

    # 3. 连接 EBO MCP
    async with EboClient(EBO_URL, EBO_TOKEN) as ebo:
        try:
            prev = door.get('contact-state')      # True=关门, False=开门
        except Exception as e:
            log.error(f'读取传感器初始状态失败: {e}')
            return
        log.info(f'监控开始。当前门状态: {"关门" if prev else "开门"}')
        log.info(f'停止方式: 关闭窗口 或 删除 {os.path.basename(FLAG_FILE)}')

        last_trigger = 0.0

        try:
            while True:
                if not os.path.exists(FLAG_FILE):
                    log.info('检测到标志文件被删除，优雅退出')
                    break

                await asyncio.sleep(POLL_INTERVAL)

                try:
                    state = door.get('contact-state')
                except Exception as e:
                    log.warning(f'传感器读取失败: {e}')
                    continue

                now = time.time()
                # 开门触发条件：上一轮关门(true) 且 本轮开门(false) 且 冷却已过
                if prev is True and state is False and (now - last_trigger) >= COOLDOWN:
                    last_trigger = now
                    log.info('>>> 检测到开门，触发迎宾 <<<')
                    try:
                        await welcome_flow(ebo, light, api)
                    except Exception as e:
                        log.error(f'迎宾流程异常: {e}')

                prev = state
        finally:
            # 任何退出路径（标志文件删除/异常/Ctrl+C 取消任务）都同步清理现场
            log.info('准备清理现场（停音乐、停跟随、关灯）')
            try:
                await cleanup_scene(ebo, light)
            except Exception as e:
                log.warning(f'清理现场异常: {e}')


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info('收到 Ctrl+C，退出')
    finally:
        try:
            if os.path.exists(FLAG_FILE):
                os.remove(FLAG_FILE)
        except OSError:
            pass
