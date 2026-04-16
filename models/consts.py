from __future__ import annotations
from enum import Enum
from dataclasses import dataclass

# ============================================================
# 常量
# ============================================================
TOTAL_TIME = 420  # 比赛总时长，单位为秒
ALL_STATES = "ALL_STATES"


UNKNOWN = 0
ALLY = "ALLY"
ENEMY = "ENEMY"
ALL_SIDES = "ALL_SIDES"

# RED = "RED"
# BLUE = "BLUE"
class Sides(Enum):
    UNKNOWN = UNKNOWN
    RED = 1
    BLUE = 2
    
# BASE = "BASE"
# OUTPOST = "OUTPOST"
# ALL_BUILDINGS = "ALL_BUILDINGS"
class BuildingTypes(Enum):
    UNKNOWN = UNKNOWN
    BASE = 1
    OUTPOST = 2

HEALTH = "HEALTH"
STATUS = "STATUS"
SHIELD = "SHIELD"

# HERO = "HERO"
# ENGINEER = "ENGINEER"
# INFANTRY = "INFANTRY"
# AIR = "AIR"
# SENTRY = "SENTRY"
# DART = "DART"
# RADAR = "RADAR"
class RobotTypes(Enum):
    UNKNOWN = UNKNOWN
    HERO = 1
    ENGINEER = 2
    INFANTRY = 3
    AIR = 4
    SENTRY = 5
    DART = 6
    RADAR = 7

@dataclass
class PlayerTypes:
    Side: Sides = Sides.UNKNOWN
    Robot: RobotTypes = RobotTypes.UNKNOWN
    Infantry_Select: int = 0  # 仅当 Robot 是 INFANTRY 时有效，表示三名步兵中的哪一名被选中（1、2 或 3）

    def get_cli_id(self) -> int:
        """根据玩家类型获取对应的 MQTT client_id。"""
        if self.Side == Sides.UNKNOWN or self.Robot == RobotTypes.UNKNOWN:
            raise ValueError(f"无法获取 client_id，因为玩家类型不完整: {self}")
        
        # 构建机器人名称
        color_prefix = self.Side.name
        robot_suffix = self.Robot.name
        robot_name: str = f"{color_prefix}_{robot_suffix}"
        
        # 获取 client_id
        res = get_cli_id_by_name(robot_name)
        if isinstance(res, tuple):
            if self.Robot != RobotTypes.INFANTRY:
                raise ValueError(f"机器人 {robot_name} 对应多个 client_id，但玩家类型中 Robot 不是 INFANTRY: {self}")
            if self.Infantry_Select not in (1, 2, 3):
                raise ValueError(f"玩家类型中 Infantry_Select 必须是 1、2 或 3，但得到的是 {self.Infantry_Select}: {self}")
            return res[self.Infantry_Select - 1]  # 根据选择返回对应的 client_id
        else:
            return res


RED_HERO = "RED_HERO"
RED_ENGINEER = "RED_ENGINEER"
RED_INFANTRY = "RED_INFANTRY"
RED_AIR = "RED_AIR"
RED_SENTRY = "RED_SENTRY"
RED_DART = "RED_DART"
RED_RADAR = "RED_RADAR"
RED_OUTPOST = "RED_OUTPOST"
RED_BASE = "RED_BASE"

BLUE_HERO = "BLUE_HERO"
BLUE_ENGINEER = "BLUE_ENGINEER"
BLUE_INFANTRY = "BLUE_INFANTRY"
BLUE_AIR = "BLUE_AIR"
BLUE_SENTRY = "BLUE_SENTRY"
BLUE_DART = "BLUE_DART"
BLUE_RADAR = "BLUE_RADAR"
BLUE_OUTPOST = "BLUE_OUTPOST"
BLUE_BASE = "BLUE_BASE"

REFREE_SERVER = "REFREE_SERVER"
# ============================================================
# 机器人 ID 映射
# ============================================================
# ID_TO_NAME: 机器人数字 ID (1, 2, 3...) -> 名称 (RED_HERO, RED_ENGINEER...)
# 用于裁判系统下发消息中的 robot_id 字段
ID_TO_NAME: dict[int, str] = {
    # 红方
    1: RED_HERO,
    2: RED_ENGINEER,
    3: RED_INFANTRY,
    4: RED_INFANTRY,
    5: RED_INFANTRY,
    6: RED_AIR,
    7: RED_SENTRY,
    8: RED_DART,
    9: RED_RADAR,
    10: RED_OUTPOST,
    11: RED_BASE,
    # 蓝方
    101: BLUE_HERO,
    102: BLUE_ENGINEER,
    103: BLUE_INFANTRY,
    104: BLUE_INFANTRY,
    105: BLUE_INFANTRY,
    106: BLUE_AIR,
    107: BLUE_SENTRY,
    108: BLUE_DART,
    109: BLUE_RADAR,
    110: BLUE_OUTPOST,
    111: BLUE_BASE,
}

# NAME_TO_ID: 名称 -> 数字 ID 的反向映射
NAME_TO_ID: dict[str, int | tuple[int, ...]] = {v: k for k, v in ID_TO_NAME.items()}

# CLIENT_ID_TO_NAME: 选手端十六进制 ID (0x0101, 0x0102...) -> 名称
# 用于 MQTT client_id 连接参数
NAME_TO_CLIENT_ID: dict[str, int | tuple[int, ...]] = {
    RED_HERO: 0x0101,
    RED_ENGINEER: 0x0102,
    RED_INFANTRY: (0x0103, 0x0104, 0x0105),
    RED_AIR: 0x0106,
    BLUE_HERO: 0x0165,
    BLUE_ENGINEER: 0x0166,
    BLUE_INFANTRY: (0x0167, 0x0168, 0x0169),
    BLUE_AIR: 0x016A,
    REFREE_SERVER: 0x8080,
}

# CLIENT_ID_TO_NAME: 选手端十六进制 ID -> 名称
CLIENT_ID_TO_NAME: dict[int, str] = {}

# 反向构建映射
for name, client_ids in NAME_TO_CLIENT_ID.items():
    if isinstance(client_ids, tuple):
        # 如果是元组，遍历每个ID
        for client_id in client_ids:
            CLIENT_ID_TO_NAME[client_id] = name
    else:
        # 如果是单个ID
        CLIENT_ID_TO_NAME[client_ids] = name

ALLOWED_CLIENT_ID: list[int] = list(CLIENT_ID_TO_NAME.keys())

DOWNLINK_TOPICS: set[str] = {
    "GameStatus", "GlobalUnitStatus", "GlobalLogisticsStatus",
    "GlobalSpecialMechanism", "Event", "RobotInjuryStat",
    "RobotRespawnStatus", "RobotStaticStatus", "RobotDynamicStatus",
    "RobotModuleStatus", "RobotPosition", "Buff", "PenaltyInfo",
    "RobotPathPlanInfo", "RadarInfoToClient", 
    "TechCoreMotionStateSync", "RobotPerformanceSelectionSync",
    "DeployModeStatusSync", "RuneStatusSync", "SentryStatusSync",
    "DartSelectTargetStatusSync", "SentryCtrlResult", "AirSupportStatusSync",
    "CustomByteBlock"
}

UPLINK_TOPICS: set[str] = {
    "CommonCommand", "RobotPerformanceSelectionCommand",
    "HeroDeployModeEventCommand", "RuneActivateCommand", "DartCommand","AirsupportCommand",
    "MapClickInfoNotify", "AssemblyCommand", "SentryCtrlCommand",

    "KeyboardMouseControl", "CustomControl"
}

ALL_TOPICS: set[str] = DOWNLINK_TOPICS.union(UPLINK_TOPICS)

def get_cli_id_by_name(name: str) -> int | tuple[int, ...]:
    """根据机器人名称获取对应的 MQTT client_id。"""
    if name not in NAME_TO_CLIENT_ID:
        raise ValueError(f"未知的机器人名称: {name}")
    return NAME_TO_CLIENT_ID[name]

def get_id_by_name(name: str):
    """根据机器人名称获取对应的数字 ID。"""
    if name not in NAME_TO_ID:
        raise ValueError(f"未知的机器人名称: {name}")
    return NAME_TO_ID[name]

if __name__ == "__main__":
    # 英雄测试（普通兵种）
    player = PlayerTypes(Sides.BLUE, RobotTypes.HERO)
    print(player)
    id_1 = player.get_cli_id()
    print(id_1, id_1 == 0x0165)
    # 步兵测试(红2步兵，client_id：0x0104)(索引从1开始)
    player = PlayerTypes(Sides.RED, RobotTypes.INFANTRY, Infantry_Select=2)
    print(player)
    id_2 = player.get_cli_id()
    print(id_2, id_2 == 0x0104)