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
    "GameStatus": pb.GameStatus,  # pyright: ignore[reportAny]
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


    

if __name__ == "__main__": 
    pass
