# protobuf_models.py
# 需要先根据协议文档生成proto文件，然后用protoc编译成Python类

"""
示例proto文件片段 (robomaster.proto):

message GameStatus {
    uint32 current_round = 1;
    uint32 total_rounds = 2;
    uint32 red_score = 3;
    uint32 blue_score = 4;
    uint32 current_stage = 5;
    int32 stage_remain_time = 6;
    int32 stage_elapsed_time = 7;
    bool is_paused = 8;
}

编译命令:
protoc --python_out=. robomaster.proto
"""

from logging import getLogger
logger = getLogger(__name__)

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[0]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from google.protobuf.message import Message
from protocol import messages_pb2 as _messages_pb2  # noqa: E402
from typing import Any, cast
pb = cast(Any, _messages_pb2)

DOWN_TOPIC2MODEL_MAP = {
    "GameStatus": pb.GameStatus,
    "GlobalUnitStatus": pb.GlobalUnitStatus,
    "GlobalLogisticsStatus": pb.GlobalLogisticsStatus,
    "GlobalSpecialMechanism": pb.GlobalSpecialMechanism,
    "Event": pb.Event,
    "RobotInjuryStat": pb.RobotInjuryStat,
    "RobotRespawnStatus": pb.RobotRespawnStatus,
    "RobotStaticStatus": pb.RobotStaticStatus,
    "RobotDynamicStatus": pb.RobotDynamicStatus,
    "RobotModuleStatus": pb.RobotModuleStatus,
    "RobotPosition": pb.RobotPosition,
    "Buff": pb.Buff,
    "PenaltyInfo": pb.PenaltyInfo,
    "RobotPathPlanInfo": pb.RobotPathPlanInfo,
    "RadarInfoToClient": pb.RadarInfoToClient,
    "CustomByteBlock": pb.CustomByteBlock,
    "TechCoreMotionStateSync": pb.TechCoreMotionStateSync,
    "RobotPerformanceSelectionSync": pb.RobotPerformanceSelectionSync,
    "DeployModeStatusSync": pb.DeployModeStatusSync,
    "RuneStatusSync": pb.RuneStatusSync,
    "SentryStatusSync": pb.SentryStatusSync,
    "DartSelectTargetStatusSync": pb.DartSelectTargetStatusSync,
    "SentryCtrlResult": pb.SentryCtrlResult,
    "AirSupportStatusSync": pb.AirSupportStatusSync
}

UPLINK_TOPIC2MODEL_MAP = {
    "KeyboardMouseControl": pb.KeyboardMouseControl,
    "CustomControl": pb.CustomControl,
    "MapClickInfoNotify": pb.MapClickInfoNotify,
    "AssemblyCommand": pb.AssemblyCommand,
    "RobotPerformanceSelectionCommand": pb.RobotPerformanceSelectionCommand,
    "CommonCommand": pb.CommonCommand,
    "HeroDeployModeEventCommand": pb.HeroDeployModeEventCommand,
    "RuneActivateCommand": pb.RuneActivateCommand,
    "DartCommand": pb.DartCommand,
    "SentryCtrlCommand": pb.SentryCtrlCommand,
    "AirSupportCommand": pb.AirSupportCommand
}

class ProtobufParser:
    @staticmethod
    def parse_game_status(data: bytes) -> Any:
        msg = pb.GameStatus()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_global_unit_status(data: bytes) -> pb.GlobalUnitStatus:  # type: ignore
        msg = pb.GlobalUnitStatus()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_global_logistics_status(data: bytes) -> pb.GlobalLogisticsStatus:  # type: ignore
        msg = pb.GlobalLogisticsStatus()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_global_special_mechanism(data: bytes) -> pb.GlobalSpecialMechanism:  # type: ignore
        msg = pb.GlobalSpecialMechanism()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_event(data: bytes) -> pb.Event:  # type: ignore
        msg = pb.Event()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_robot_injury_stat(data: bytes) -> pb.RobotInjuryStat:  # type: ignore
        msg = pb.RobotInjuryStat()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_robot_respawn_status(data: bytes) -> pb.RobotRespawnStatus:  # type: ignore
        msg = pb.RobotRespawnStatus()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_robot_static_status(data: bytes) -> pb.RobotStaticStatus:  # type: ignore
        msg = pb.RobotStaticStatus()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_robot_dynamic_status(data: bytes) -> pb.RobotDynamicStatus:  # type: ignore
        msg = pb.RobotDynamicStatus()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_robot_module_status(data: bytes) -> pb.RobotModuleStatus:  # type: ignore
        msg = pb.RobotModuleStatus()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_robot_position(data: bytes) -> pb.RobotPosition:  # type: ignore
        msg = pb.RobotPosition()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_buff(data: bytes) -> pb.Buff:  # type: ignore
        msg = pb.Buff()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_penalty_info(data: bytes) -> pb.PenaltyInfo:  # type: ignore
        msg = pb.PenaltyInfo()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_robot_path_plan_info(data: bytes) -> pb.RobotPathPlanInfo:  # type: ignore
        msg = pb.RobotPathPlanInfo()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_radar_info_to_client(data: bytes) -> pb.RadarInfoToClient:  # type: ignore
        msg = pb.RadarInfoToClient()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_custom_byte_block(data: bytes) -> pb.CustomByteBlock:  # type: ignore
        msg = pb.CustomByteBlock()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_tech_core_motion_state_sync(data: bytes) -> pb.TechCoreMotionStateSync:  # type: ignore
        msg = pb.TechCoreMotionStateSync()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_robot_performance_selection_sync(data: bytes) -> pb.RobotPerformanceSelectionSync:  # type: ignore
        msg = pb.RobotPerformanceSelectionSync()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_deploy_mode_status_sync(data: bytes) -> pb.DeployModeStatusSync:  # type: ignore
        msg = pb.DeployModeStatusSync()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_rune_status_sync(data: bytes) -> pb.RuneStatusSync:  # type: ignore
        msg = pb.RuneStatusSync()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_sentry_status_sync(data: bytes) -> pb.SentryStatusSync:  # type: ignore
        msg = pb.SentryStatusSync()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_dart_status(data: bytes) -> pb.DartSelectTargetStatusSync:  # type: ignore
        msg = pb.DartSelectTargetStatusSync()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_sentry_ctrl_result(data: bytes) -> pb.SentryCtrlResult:  # type: ignore
        msg = pb.SentryCtrlResult()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_air_support_status_sync(data: bytes) -> pb.AirSupportStatusSync:  # type: ignore
        msg = pb.AirSupportStatusSync()  # type: ignore
        msg.ParseFromString(data)
        return msg

    # === 上行消息解析方法 ===
    @staticmethod
    def parse_keyboard_mouse_control(data: bytes) -> pb.KeyboardMouseControl:  # type: ignore
        msg = pb.KeyboardMouseControl()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_custom_control(data: bytes) -> pb.CustomControl:  # type: ignore
        msg = pb.CustomControl()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_map_click_info_notify(data: bytes) -> pb.MapClickInfoNotify:  # type: ignore
        msg = pb.MapClickInfoNotify()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_assembly_command(data: bytes) -> pb.AssemblyCommand:  # type: ignore
        msg = pb.AssemblyCommand()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_robot_performance_selection_command(data: bytes) -> pb.RobotPerformanceSelectionCommand:  # type: ignore
        msg = pb.RobotPerformanceSelectionCommand()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_common_command(data: bytes) -> pb.CommonCommand:  # type: ignore
        msg = pb.CommonCommand()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_hero_deploy_mode_event_command(data: bytes) -> pb.HeroDeployModeEventCommand:  # type: ignore
        msg = pb.HeroDeployModeEventCommand()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_rune_activate_command(data: bytes) -> pb.RuneActivateCommand:  # type: ignore
        msg = pb.RuneActivateCommand()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_dart_command(data: bytes) -> pb.DartCommand:  # type: ignore
        msg = pb.DartCommand()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_sentry_ctrl_command(data: bytes) -> pb.SentryCtrlCommand:  # type: ignore
        msg = pb.SentryCtrlCommand()  # type: ignore
        msg.ParseFromString(data)
        return msg

    @staticmethod
    def parse_air_support_command(data: bytes) -> pb.AirSupportCommand:  # type: ignore
        msg = pb.AirSupportCommand()  # type: ignore
        msg.ParseFromString(data)
        return msg

class ProtobufSerializer:
    @staticmethod
    def serialize_message(msg: Message) -> bytes:
        return msg.SerializeToString()
    

if __name__ == "__main__":
    
    p = ProtobufParser()
    g = pb.GameStatus(current_round=1, total_rounds=3, red_score=10, blue_score=20, current_stage=2, stage_countdown_sec=120, stage_elapsed_sec=30, is_paused=True)
    data = g.SerializeToString()
    print(f"Serialized GameStatus: {data}")
    parsed = p.parse_game_status(data)
    print(f"Parsed GameStatus: {parsed}")
