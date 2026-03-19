"""
监听 SharkDataSever 与 Reflex 客户端之间的 MQTT 双向数据，并输出 JSON 行日志。

默认连接 127.0.0.1:3333，订阅全部 topic（#）。
优先按 topic 名使用 protocol/messages_pb2 解析 Protobuf；若失败则尝试按 UTF-8 JSON 解析。

示例:
  python debug_mqtt_json_bridge.py
  python debug_mqtt_json_bridge.py --host 192.168.12.1 --port 3333 --topic "#"
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import paho.mqtt.client as mqtt
from google.protobuf import json_format

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from protocol import messages_pb2


UPLINK_TOPICS = {
    "CommonCommand",
    "RobotPerformanceSelectionCommand",
    "HeroDeployModeEventCommand",
    "RuneActivateCommand",
    "DartCommand",
    "MapSentryPathSearchCommand",
    "SentryPathControlCommand",
    "MapRadarMarkCommand",
    "AirsupportCommand",
    "TechCoreAssembleOperationCommand",
}

DOWNLINK_TOPICS = {
    "GameStatus",
    "GlobalUnitStatus",
    "GlobalLogisticsStatus",
    "GlobalSpecialMechanism",
    "Event",
    "RobotInjuryStat",
    "RobotRespawnStatus",
    "RobotStaticStatus",
    "RobotDynamicStatus",
    "RobotModuleStatus",
    "RobotPosition",
    "Buff",
    "PenaltyInfo",
    "RobotPathPlanInfo",
    "RaderInfoToClient",
    "CustomByteBlock",
    "TechCoreMotionStateSync",
    "RobotPerformanceSelectionSync",
    "DeployModeStatusSync",
    "RuneStatusSync",
    "SentinelStatusSync",
    "DartSelectTargetStatusSync",
    "GuardCtrlResult",
    "AirSupportStatusSync",
}


def utc_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def reason_code_to_json(reason_code: Any) -> dict[str, Any]:
    """Normalize paho reason code across callback API versions."""
    code_value: int | None = None

    raw_value = getattr(reason_code, "value", None)
    if isinstance(raw_value, (int, float)):
        code_value = int(raw_value)
    else:
        try:
            code_value = int(reason_code)
        except Exception:
            code_value = None

    return {
        "code": code_value,
        "name": str(reason_code),
    }


def tail_topic(topic: str) -> str:
    return topic.split("/")[-1]


def classify_direction(topic_name: str) -> str:
    if topic_name in UPLINK_TOPICS or topic_name.endswith("Command"):
        return "reflex_to_shark"
    if topic_name in DOWNLINK_TOPICS or topic_name.endswith("Status") or topic_name.endswith("Sync"):
        return "shark_to_reflex"
    return "unknown"


def decode_payload(topic_name: str, payload: bytes) -> tuple[str, Any, str | None]:
    message_cls = getattr(messages_pb2, topic_name, None)
    if message_cls is not None:
        try:
            message = message_cls()
            message.ParseFromString(payload)
            payload_dict = json_format.MessageToDict(
                message,
                preserving_proto_field_name=True,
                use_integers_for_enums=True,
            )

            # Proto3 标量默认值不会序列化。部署退出时 mode=0 也需要在调试日志中可见。
            if topic_name == "HeroDeployModeEventCommand" and "mode" not in payload_dict:
                payload_dict["mode"] = int(getattr(message, "mode", 0))

            # 飞镖指令中的 bool 默认值 false 在 proto3 下会被省略，这里补齐便于调试对比。
            if topic_name == "DartCommand":
                if "open" not in payload_dict:
                    payload_dict["open"] = bool(getattr(message, "open", False))
                if "launch_confirm" not in payload_dict:
                    payload_dict["launch_confirm"] = bool(getattr(message, "launch_confirm", False))

            return (
                "protobuf",
                payload_dict,
                None,
            )
        except Exception as exc:
            return ("protobuf", None, f"protobuf parse failed: {exc}")

    try:
        text = payload.decode("utf-8")
        return ("json", json.loads(text), None)
    except Exception:
        pass

    return ("binary", {"hex": payload.hex(), "size": len(payload)}, None)


def print_event(event: dict[str, Any]) -> None:
    print(json.dumps(event, ensure_ascii=False, separators=(",", ":")))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MQTT 双向 JSON 调试监听器")
    parser.add_argument("--host", default="127.0.0.1", help="MQTT 主机")
    parser.add_argument("--port", type=int, default=3333, help="MQTT 端口")
    parser.add_argument("--topic", default="#", help="订阅 topic，默认 #")
    parser.add_argument("--qos", type=int, default=1, choices=[0, 1, 2], help="订阅 QoS")
    parser.add_argument("--client-id", default="debug-mqtt-json-bridge", help="MQTT Client ID")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    callback_api = getattr(mqtt, "CallbackAPIVersion", None)
    try:
        if callback_api is None:
            raise AttributeError("CallbackAPIVersion unavailable")
        client = mqtt.Client(callback_api.VERSION2, client_id=args.client_id)
    except Exception:
        client = mqtt.Client(client_id=args.client_id)

    def on_connect(_client, _userdata, _flags, reason_code, _properties=None):
        print_event(
            {
                "ts": utc_iso(),
                "type": "connect",
                "host": args.host,
                "port": args.port,
                "reason": reason_code_to_json(reason_code),
                "subscribe": {"topic": args.topic, "qos": args.qos},
            }
        )
        _client.subscribe(args.topic, qos=args.qos)

    def on_disconnect(_client, _userdata, _flags, reason_code, _properties=None):
        print_event(
            {
                "ts": utc_iso(),
                "type": "disconnect",
                "reason": reason_code_to_json(reason_code),
            }
        )

    def on_message(_client, _userdata, msg):
        topic_name = tail_topic(msg.topic)
        direction = classify_direction(topic_name)
        payload_type, decoded, decode_error = decode_payload(topic_name, msg.payload)

        event: dict[str, Any] = {
            "ts": utc_iso(),
            "type": "message",
            "direction": direction,
            "topic": msg.topic,
            "topic_name": topic_name,
            "qos": msg.qos,
            "retain": bool(msg.retain),
            "payload_type": payload_type,
            "payload_size": len(msg.payload),
            "payload": decoded,
        }
        if decode_error:
            event["decode_error"] = decode_error

        print_event(event)

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_message = on_message

    try:
        client.connect(args.host, args.port, keepalive=30)
        client.loop_forever()
        return 0
    except KeyboardInterrupt:
        print_event({"ts": utc_iso(), "type": "stop", "reason": "keyboard_interrupt"})
        return 0
    except Exception as exc:
        print_event({"ts": utc_iso(), "type": "fatal", "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
