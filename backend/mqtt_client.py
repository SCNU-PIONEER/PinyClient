"""
RoboMaster MQTT 客户端模块
负责与裁判系统服务器建立 MQTT 连接，接收并解析下行数据。
状态机逻辑已分离到 states.py，保持解耦。
"""
from __future__ import annotations

import logging
import os
import time
import random
import threading
import queue
from dataclasses import dataclass
from typing import Callable, Dict, Any

import paho.mqtt.client as mqtt
from google.protobuf.json_format import MessageToDict

from states import RMClientStates, RED, BLUE, ALLY, ALL_STATES, CLIENT_ID_TO_NAME
from protobuf_models import DOWN_TOPIC2MODEL_MAP, UPLINK_TOPIC2MODEL_MAP


# ============================================================
# 彩色日志配置
# ============================================================
def _setup_logger(name: str = "pioneer") -> logging.Logger:
    """
    配置彩色日志，支持通过 PIONEER_LOG_LEVEL 环境变量切换级别。
    生产环境设为 INFO，调试时设为 DEBUG。
    """
    _COLORS = {
        "RESET":   "\033[0m",
        "RED":     "\033[91m",
        "GREEN":   "\033[92m",
        "YELLOW":  "\033[93m",
        "BLUE":    "\033[94m",
        "MAGENTA": "\033[95m",
        "CYAN":    "\033[96m",
        "GRAY":    "\033[90m",
    }
    _LEVEL_COLOR = {
        "DEBUG":   _COLORS["GRAY"],
        "INFO":    _COLORS["BLUE"],
        "WARNING": _COLORS["YELLOW"],
        "ERROR":   _COLORS["RED"],
        "CRITICAL": _COLORS["MAGENTA"],
    }

    logger = logging.getLogger(name)
    level_str = os.environ.get("PIONEER_LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, level_str, logging.INFO))
    logger.handlers.clear()

    class ColorFormatter(logging.Formatter):
        def format(self, record):
            color = _LEVEL_COLOR.get(record.levelname, _COLORS["RESET"])
            record.levelname = f"{color}{record.levelname}{_COLORS['RESET']}"
            record.name = f"{_COLORS['CYAN']}{record.name}{_COLORS['RESET']}"
            return super().format(record)

    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    fmt = "%(asctime)s | %(levelname)-10s | %(name)s | %(message)s"
    handler.setFormatter(ColorFormatter(fmt, datefmt="%H:%M:%S"))
    logger.addHandler(handler)
    return logger


logger = _setup_logger()


# ============================================================
# 常量
# ============================================================
NAME_TO_ID: Dict[str, Any] = {
    "RED_HERO": 1, "RED_ENGINEER": 2,
    "RED_INFANTRY": (3, 4, 5), "RED_AIR": 6,
    "RED_SENTRY": 7, "RED_DART": 8,
    "RED_RADAR": 9, "RED_OUTPOST": 10, "RED_BASE": 11,
    "BLUE_HERO": 101, "BLUE_ENGINEER": 102,
    "BLUE_INFANTRY": (103, 104, 105), "BLUE_AIR": 106,
    "BLUE_SENTRY": 107, "BLUE_DART": 108,
    "BLUE_RADAR": 109, "BLUE_OUTPOST": 110, "BLUE_BASE": 111,
}

ALLOWED_CLIENT_ID: list[int] = []
for _ids in NAME_TO_ID.values():
    ALLOWED_CLIENT_ID.extend(_ids) if isinstance(_ids, tuple) else ALLOWED_CLIENT_ID.append(_ids)

DOWNLINK_TOPICS = {
    "GameStatus", "GlobalUnitStatus", "GlobalLogisticsStatus",
    "GlobalSpecialMechanism", "Event", "RobotInjuryStat",
    "RobotRespawnStatus", "RobotStaticStatus", "RobotDynamicStatus",
    "RobotModuleStatus", "RobotPosition", "Buff", "PenaltyInfo",
    "RobotPathPlanInfo", "RadarInfoToClient", "CustomByteBlock",
    "TechCoreMotionStateSync", "RobotPerformanceSelectionSync",
    "DeployModeStatusSync", "RuneStatusSync", "SentryStatusSync",
    "DartSelectTargetStatusSync", "SentryCtrlResult", "AirSupportStatusSync",
}

UPLINK_TOPICS = {
    "CommonCommand", "RobotPerformanceSelectionCommand",
    "HeroDeployModeEventCommand", "RuneActivateCommand", "DartCommand",
    "MapSentryPathSearchCommand", "SentryPathControlCommand",
    "MapRadarMarkCommand", "AirsupportCommand",
    "TechCoreAssembleOperationCommand",
}

# ============================================================
# 主类
# ============================================================
class RoboMasterMQTT:
    """
    MQTT 客户端，连接裁判系统服务器，接收比赛数据并更新状态机。
    """

    # 每个 topic 对应状态机中哪些字段需要更新
    # ALL_STATES = 全量更新；列表 = 选择性更新
    UPDATE_ITEMS: Dict[str, Any] = {
        "GameStatus": ["red_score", "blue_score", "stage_countdown_sec", "stage_elapsed_sec"],
        **{topic: ALL_STATES for topic in DOWNLINK_TOPICS if topic != "GameStatus"},
    }

    def __init__(self, client_id: int, host: str = "192.168.12.1", port: int = 3333):
        if client_id not in ALLOWED_CLIENT_ID:
            logger.critical("无效的 client_id: %s，允许值: %s", client_id, ALLOWED_CLIENT_ID)
            raise ValueError(f"Invalid client_id: {client_id}")

        self.client_id = client_id
        self.host = host
        self.port = port

        # 状态机（独立类，可单独提取给 HTTP 模块使用）
        ally_color = RED if client_id < 100 else BLUE
        self.states = RMClientStates(ally_color=ally_color)

        # MQTT 客户端
        self._mqtt = mqtt.Client(client_id=str(client_id))
        self._mqtt.on_connect    = self._on_connect
        self._mqtt.on_message   = self._on_message
        self._mqtt.on_disconnect = self._on_disconnect

        # 消息队列（有界，满了丢弃最旧消息）
        self._queue: queue.Queue[tuple[str, bytes]] = queue.Queue(maxsize=500)

        # 回调表
        self._callbacks: Dict[str, Callable[[bytes], None]] = {}

        # 发布锁
        self._publish_lock = threading.Lock()

        logger.info(
            "MQTT[%s] 初始化完成，连接目标 %s:%s",
            CLIENT_ID_TO_NAME.get(client_id, client_id), host, port
        )

    # --------------------------------------------------------
    # MQTT 生命周期
    # --------------------------------------------------------
    def start(self) -> None:
        """启动 MQTT 客户端（连接 + 消息处理线程）。"""
        self._register_callbacks()
        self._connect_loop()
        threading.Thread(target=self._process_messages, name="msg_processor", daemon=True).start()
        logger.info("MQTT 客户端已启动")

    def stop(self) -> None:
        """断开连接并停止线程。"""
        self._mqtt.loop_stop()
        self._mqtt.disconnect()
        logger.info("MQTT 客户端已停止")

    def _connect_loop(self) -> None:
        """指数退避重连。"""
        max_delay = 30
        delay = 1.0
        attempt = 0
        while True:
            try:
                self._mqtt.connect(self.host, self.port, keepalive=60)
                self._mqtt.loop_start()
                logger.info("已连接到 %s:%s", self.host, self.port)
                return
            except Exception as e:
                attempt += 1
                logger.warning("第 %d 次连接失败: %s，%.1fs 后重试...", attempt, e, delay)
                time.sleep(delay)
                delay = min(delay * 1.5 + random.uniform(0, 0.5), max_delay)

    def _on_connect(self, _client, _userdata, flags, rc: int) -> None:
        if rc == 0:
            logger.info("连接成功，已订阅 %d 个 topic", len(DOWNLINK_TOPICS))
            for topic in DOWNLINK_TOPICS:
                self._mqtt.subscribe(topic)
        else:
            logger.error("连接失败，rc=%d", rc)

    def _on_message(self, _client, _userdata, msg) -> None:
        try:
            self._queue.put_nowait((msg.topic, msg.payload))
        except queue.Full:
            logger.warning("消息队列已满，丢弃 topic=%s", msg.topic)

    def _on_disconnect(self, _client, _userdata, rc: int) -> None:
        logger.warning("连接断开 (rc=%d)，正在重连...", rc)
        self._connect_loop()

    # --------------------------------------------------------
    # 消息处理
    # --------------------------------------------------------
    def _process_messages(self) -> None:
        """消息处理循环：从队列取消息 → 解析 → 更新状态机。"""
        logger.info("消息处理线程已启动")
        while True:
            topic, payload = self._queue.get()
            if topic in self._callbacks:
                try:
                    self._callbacks[topic](payload)
                except Exception as e:
                    logger.error("处理 %s 时出错: %s", topic, e)

    def _register_callbacks(self) -> None:
        """
        批量注册所有 topic 的回调。
        所有 topic 共用同一个解析函数，保持代码简洁；
        特殊逻辑可在各自回调中添加。
        """
        def parse_and_update(topic: str, payload: bytes) -> None:
            """解析 Protobuf 消息并更新状态机。"""
            model_cls = DOWN_TOPIC2MODEL_MAP.get(topic)
            if model_cls is None:
                logger.warning("未找到 topic '%s' 的 Protobuf 模型，跳过", topic)
                return

            msg = model_cls()
            try:
                msg.ParseFromString(payload)
            except Exception as e:
                logger.error("解析 %s 失败: %s", topic, e)
                return

            # 按配置更新状态机
            update_spec = self.UPDATE_ITEMS.get(topic, ALL_STATES)
            if update_spec == ALL_STATES:
                msg_dict = MessageToDict(msg, preserving_proto_field_name=True)
                self.states.update(msg_dict)
                logger.debug("[%s] 全量更新: %s", topic, msg_dict)
            elif isinstance(update_spec, list):
                for field in update_spec:
                    val = getattr(msg, field, None)
                    self.states.update({field: val})
                logger.debug("[%s] 选择更新: %s", topic, update_spec)

        for topic in DOWNLINK_TOPICS:
            self._callbacks[topic] = lambda payload, t=topic: parse_and_update(t, payload)
        logger.debug("已注册 %d 个 topic 回调", len(self._callbacks))

    # --------------------------------------------------------
    # 状态查询（委托给状态机）
    # --------------------------------------------------------
    def state_update(self, state, msgs: Any = None) -> None:
        """兼容旧 API，内部转发给状态机。"""
        if state == ALL_STATES and msgs is not None:
            self.states.update(MessageToDict(msgs, preserving_proto_field_name=True))

    # --------------------------------------------------------
    # 发送指令
    # --------------------------------------------------------
    def publish(self, topic: str, message: bytes) -> None:
        """发送上行指令到裁判系统服务器。"""
        with self._publish_lock:
            result = self._mqtt.publish(topic, message)
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                logger.error("发布 %s 失败，rc=%d", topic, result.rc)
            else:
                logger.debug("已发布 %s", topic)

    def publish_command(self, topic: str, msg) -> None:
        """序列化 Protobuf 消息并发送（便捷封装）。"""
        if topic not in UPLINK_TOPIC2MODEL_MAP:
            logger.warning("未知上行 topic: %s", topic)
            return
        data = msg.SerializeToString()
        self.publish(topic, data)


# ============================================================
# 入口
# ============================================================
if __name__ == "__main__":
    r = RoboMasterMQTT(client_id=NAME_TO_ID["RED_HERO"], host="localhost", port=3333)
    r.start()
