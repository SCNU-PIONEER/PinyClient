"""
RoboMaster 状态机模块
与 MQTT 逻辑解耦，可独立使用，供后端 HTTP 接口或前端直接读取。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from typing import Literal


# ============================================================
# 常量
# ============================================================
TOTAL_TIME = 420  # 比赛总时长，单位为秒
ALL_STATES = "ALL_STATES"


UNKNOWN = "UNKNOWN"
ALLY = "ALLY"
ENEMY = "ENEMY"
ALL_SIDES = "ALL_SIDES"

RED = "RED"
BLUE = "BLUE"
ALL_COLORS = "ALL_COLORS"

BASE = "BASE"
OUTPOST = "OUTPOST"
ALL_BUILDINGS = "ALL_BUILDINGS"

HEALTH = "HEALTH"
STATUS = "STATUS"
SHIELD = "SHIELD"

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

# ============================================================
# 数据类
# ============================================================

@dataclass
class RMGameStatus:
    """
    比赛状态信息
    目前包含：当前回合数、总回合数、红蓝双方得分、当前阶段、阶段倒计时、阶段已过时间、是否暂停等
    """
    CURRENT_ROUND: int
    TOTAL_ROUNDS: int
    RED_SCORE: int
    BLUE_SCORE: int
    CURRENT_STAGE: Literal[0, 1, 2, 3, 4, 5]
    STAGE_COUNTDOWN_SEC: int
    STAGE_ELAPSED_SEC: int
    IS_PAUSED: bool

    def get_stage_name(self) -> str:
        """
        获取当前阶段的名称，便于前端显示。
        """
        stage_names = {
            0: "未开始",
            1: "准备阶段",
            2: "裁判系统自检",
            3: "五秒倒计时",
            4: "比赛中",
            5: "比赛结算中",
        }
        return stage_names.get(self.CURRENT_STAGE, "未知阶段")


@dataclass
class RMTime:
    REMAINING_TIME: int
    PASSED_TIME: int
    TOTAL_TIME: int

    def get_second_time_messgae(self):
        """
        获取剩余时间和总时间的秒数格式字符串，便于前端显示。
        """
        return f"{self.REMAINING_TIME}/{self.TOTAL_TIME}"

    def get_min_sec_time_message(self):
        """
        获取剩余时间和总时间的分钟:秒格式字符串，便于前端显示。
        """
        remaining_min = self.REMAINING_TIME // 60
        remaining_sec = self.REMAINING_TIME % 60
        total_min = self.TOTAL_TIME // 60
        total_sec = self.TOTAL_TIME % 60
        return f"{remaining_min}:{remaining_sec:02d}/{total_min}:{total_sec:02d}"


@dataclass
class RMBaseStatus:
    """
    基地状态信息
    目前包含：血量、状态、护盾等
    """

    HEALTH: int
    STATUS: Literal[0, 1, 2]
    SHIELD: int

    def get_status_message(self):
        status_messages = {
            0: "无敌",
            1: "解除无敌，护甲未展开",
            2: "解除无敌，护甲展开",
        }
        return status_messages.get(self.STATUS, "未知状态")


@dataclass
class RMOutpostStatus:
    """
    前哨站状态信息
    目前包含：血量、状态、护盾等
    """
    HEALTH: int
    STATUS: Literal[0, 1, 2, 3, 4, 5]
    SHIELD: int

    def get_status_message(self):
        status_messages = {
            0: "无敌",
            1: "存活，解除无敌，中部装甲旋转",
            2: "存活，解除无敌，中部装甲停转",
            3: "被击毁，不可重建",
            4: "被击毁，可重建",
            5: "被击毁，重建中",
        }
        return status_messages.get(self.STATUS, "未知状态")


@dataclass
class RMBuildingStatus:
    BASE: RMBaseStatus
    OUTPOST: RMOutpostStatus


@dataclass
class RMAllBuildingsStatus:
    """
    RMAllBuildingsStatus -> RMBuildingStatus -> RMBaseStatus/RMOutpostStatus
    """
    RED: RMBuildingStatus
    BLUE: RMBuildingStatus

    def get_side_status(self, side2color: Dict[str, str], side: str = ALLY) -> RMBuildingStatus:
        return getattr(self, side2color[side])


@dataclass
class RMScore:
    RED: int
    BLUE: int
    
    def get_by_color(self, color: str):
        return getattr(self, color.upper())
    
    def get_by_side(self, side2color: Dict[str, str], side: str):
        return getattr(self, side2color[side])
    
    def get_s2s_score(self):
        return getattr(self, ALLY) + "/" + getattr(self, ENEMY)


@dataclass
class RMDamage:
    ALLY: int
    ENEMY: int

    def get_by_side(self, side: str):
        return getattr(self, side.upper())
    
    def get_s2s_damage(self):
        return str(getattr(self, ALLY)) + "/" + str(getattr(self, ENEMY))


@dataclass
class RMEconomy:
    ALLY: int
    ALLY_ALL: int

    def get_cur_total(self):
        return str(getattr(self, ALLY)) + "/" + str(getattr(self, "ALLY_ALL"))


@dataclass
class RMLevel:
    
    TECH_LEVEL: int
    ENCRYPTION_LEVEL: int


@dataclass
class RMMec:
    """
    同步正在生效的全局特殊机制，目前包含堡垒占领倒计时
    """
    MEC_ID: list[int]
    MEC_TIME: list[int]

    def get_by_id(self, mec_id: int):
        if mec_id in self.MEC_ID:
            index = self.MEC_ID.index(mec_id)
            return self.MEC_TIME[index]
        else:
            raise ValueError(f"MEC ID {mec_id} not found.")
    

@dataclass
class RMEvent:
    """
    1: 击杀事件（参数为击杀者 id+被击毁机器人 id 的拼接） 
    2: 基地、前哨站被摧毁事件（参数值为被击毁的目标 id，如蓝方前哨站为 111） 
    3: 能量机关可激活次数变化（参数值为变化后可激活次数） 
    4: 能量机关当前可进入正在激活状态（无参数值） 
    5: 当前能量机关被成功激活的灯臂数量、平均环数（参数值为激活成功臂数+平均环数的拼接） 
    6: 能量机关被激活（含激活类型） 
    7: 己方英雄进入部署模式（无参数值） 
    8: 己方英雄造成狙击伤害（参数值为累计造成狙击伤害数量） 
    9: 对方英雄造成狙击伤害（参数值为累计造成狙击伤害数量） 
    10: 己方呼叫空中支援（无参数值） 
    11: 己方空中支援被打断（参数值为对方还剩余的可打断次数） 
    12: 对方呼叫空中支援（无参数值） 
    13: 对方空中支援被打断（参数值为己方还剩余的可打断次数） 
    14: 飞镖命中（参数值为命中目标，1  为击中前哨站，2  为击中基地固定目标，3  为击中基地随机固定目标，4  为击中基地随机移动目标，5 为击中基地末端移动目标） 
    15: 双方飞镖闸门开启（参数值 1 为己方开启，2 为对方开启） 
    16: 己方基地遭到攻击（无参数值，每次触发存在 5s 内置冷却） 
    17: 双方前哨站停转（参数值 1 为己方前哨，2 为对方前哨） 
    18: 双方基地护甲展开（参数值 1 为己方基地，2 为对方基地）
    """
    EVENT_ID: int
    PARAMS: str

    EVENT_ID_TO_NAME: Dict[int, str] = field(default_factory=lambda: {
        1: "KILL",
        2: "BUILDING_DESTROYED",
        3: "MEC_ACTIVATION_COUNT_CHANGE",
        4: "MEC_ACTIVATION_READY",
        5: "MEC_ACTIVATION_SUCCESS",
        6: "MEC_ACTIVATED",
        7: "ALLY_HERO_DEPLOY_MODE",
        8: "ALLY_HERO_SNIPING_DAMAGE",
        9: "ENEMY_HERO_SNIPING_DAMAGE",
        10: "ALLY_CALL_AIR_SUPPORT",
        11: "ALLY_AIR_SUPPORT_INTERRUPTED",
        12: "ENEMY_CALL_AIR_SUPPORT",
        13: "ENEMY_AIR_SUPPORT_INTERRUPTED",
        14: "DART_HIT",
        15: "DART_GATE_OPENED",
        16: "ALLY_BASE_UNDER_ATTACK",
        17: "OUTPOST_STOPPED",
        18: "BASE_ARMOR_DEPLOYED",
    })
    NAME_TO_TEXT: Dict[str, str] = field(default_factory=lambda: {
        "KILL": "击杀事件, 击杀者: {killer_id}, 被击毁者: {destroyed_id}",
        "BUILDING_DESTROYED": "建筑被摧毁, 被击毁目标: {destroyed_id}",
        "MEC_ACTIVATION_COUNT_CHANGE": "能量机关可激活次数变化, 当前可激活次数: {count}",
        "MEC_ACTIVATION_READY": "能量机关可进入激活状态",
        "MEC_ACTIVATION_SUCCESS": "能量机关激活成功, 激活成功臂数: {arms}, 平均环数: {avg_rings}",
        "MEC_ACTIVATED": "能量机关被激活, 激活类型: {activation_type}",
        "ALLY_HERO_DEPLOY_MODE": "己方英雄进入部署模式",
        "ALLY_HERO_SNIPING_DAMAGE": "己方英雄造成狙击伤害, 累计狙击伤害: {damage}",
        "ENEMY_HERO_SNIPING_DAMAGE": "对方英雄造成狙击伤害, 累计狙击伤害: {damage}",
        "ALLY_CALL_AIR_SUPPORT": "己方呼叫空中支援",
        "ALLY_AIR_SUPPORT_INTERRUPTED": "己方空中支援被打断, 剩余可打断次数: {remaining_interrupts}",
        "ENEMY_CALL_AIR_SUPPORT": "对方呼叫空中支援",
        "ENEMY_AIR_SUPPORT_INTERRUPTED": "对方空中支援被打断, 剩余可打断次数: {remaining_interrupts}",
        "DART_HIT": "飞镖命中, 命中目标: {hit_target}",
        "DART_GATE_OPENED": "{side}飞镖闸门开启",
        "ALLY_BASE_UNDER_ATTACK": "己方基地遭到攻击",
        "OUTPOST_STOPPED": "{side}前哨站停转",
        "BASE_ARMOR_DEPLOYED": "{side}基地护甲展开",
    })

    def get_event_text(self) -> str:
        event_name = self.EVENT_ID_TO_NAME.get(self.EVENT_ID, "UNKNOWN_EVENT")
        template = self.NAME_TO_TEXT.get(event_name, "未知事件")
        # 解析 PARAMS，根据事件类型提取参数
        if event_name == "KILL":
            killer_id, destroyed_id = self.PARAMS.split(" ")
            return template.format(killer_id=CLIENT_ID_TO_NAME.get(int(killer_id), "未知玩家"), destroyed_id=CLIENT_ID_TO_NAME.get(int(destroyed_id), "未知玩家"))
        elif event_name == "BUILDING_DESTROYED":
            return template.format(destroyed_id=self.PARAMS)
        elif event_name == "MEC_ACTIVATION_COUNT_CHANGE":
            return template.format(count=self.PARAMS)
        elif event_name == "MEC_ACTIVATION_SUCCESS":
            arms, avg_rings = self.PARAMS.split(" ")
            return template.format(arms=arms, avg_rings=avg_rings)
        elif event_name == "MEC_ACTIVATED":
            return template.format(activation_type=self.PARAMS)
        elif event_name in ("ALLY_HERO_SNIPING_DAMAGE", "ENEMY_HERO_SNIPING_DAMAGE"):
            return template.format(damage=self.PARAMS)
        elif event_name in ("ALLY_AIR_SUPPORT_INTERRUPTED", "ENEMY_AIR_SUPPORT_INTERRUPTED"):
            return template.format(remaining_interrupts=self.PARAMS)
        elif event_name == "DART_HIT":
            return template.format(hit_target=self.PARAMS)
        elif event_name == "DART_GATE_OPENED":
            side = "己方" if self.PARAMS == "1" else "对方"
            return template.format(side=side)
        elif event_name in ("OUTPOST_STOPPED", "BASE_ARMOR_DEPLOYED"):
            side = "己方" if self.PARAMS == "1" else "对方"
            return template.format(side=side)
        else:
            return template


@dataclass
class RMInjury:
    """
    机器人一次存活期间累计受伤统计
     目前包含：总伤害、碰撞伤害、小口径伤害、大口径伤害、飞镖溅射伤害、模块离线伤害、完全离线伤害、惩罚伤害、服务器击杀伤害等
    """
    TOTAL_DAMAGE: int
    COLLISION_DAMAGE: int
    SMALL_PROJECTILE_DAMAGE: int
    LARGE_PROJECTILE_DAMAGE: int
    DART_SPLASH_DAMAGE: int
    MODULE_OFFLINE_DAMAGE: int
    OFFLINE_DAMAGE: int
    PENALTY_DAMAGE: int
    SERVER_KILL_DAMAGE: int
    KILLER_ID: int


@dataclass
class RMRepawn:
    """
    机器人重生信息
    目前包含：是否正在重生、重生总进度、当前重生进度、是否可以免费重生、重生所需金币、是否可以支付金币重生等
    """
    is_pending_respawn: bool
    total_respawn_progress: int
    current_respawn_progress: int
    can_free_respawn: bool
    gold_cost_for_respawn: int
    can_pay_for_respawn: bool


@dataclass
class RMStatic:
    """
    机器人静态属性
     目前包含：连接状态、场地状态、生存状态、机器人 ID、机器人类型、性能系统等级（射手/底盘）、等级、最大血量、最大热量、热量冷却速率、最大能量、最大缓冲能量、最大底盘能量等
     其中连接状态表示机器人是否在线，场地状态表示机器人所在的场地是否正常，生存状态表示机器人当前是否存活。
     机器人 ID 和类型用于区分不同的机器人，性能系统等级表示机器人当前的性能系统升级情况，等级表示机器人当前的等级。
     最大血量和热量是机器人的基本属性，热量冷却速率表示机器人热量的自然冷却速度，最大能量和缓冲能量则与机器人的技能使用相关。
     最大底盘能量则影响机器人的移动能力和某些特殊技能的使用。
     这些静态属性在比赛过程中可能会发生变化，例如连接状态可能因为网络问题而变为离线，生存状态可能因为被击毁而变为死亡，性能系统等级可能因为升级而提升等。
     因此需要实时更新这些属性以反映机器人的当前状态。
     performance_system_shooter  枚举值：
     1：冷却优先
     2：爆发优先
     3：英雄近战优先
     4：英雄远程优先 performance_system_chassis  枚举值：
     1：血量优先
     2：功率优先
     3：英雄近战优先
     4：英雄远程优先
    """
    CONNECTION_STATE: Literal[0, 1]
    FIELD_STATE: Literal[0, 1]
    ALIVE_STATE: Literal[0, 1, 2]
    ROBOT_ID: int
    ROBOT_TYPE: int
    PERFORMANCE_SYSTEM_SHOOTER: Literal[1, 2, 3, 4]
    PERFORMANCE_SYSTEM_CHASSIS: Literal[1, 2, 3, 4]
    LEVEL: int
    MAX_HEALTH: int
    MAX_HEAT: int
    HEAT_COOLDOWN_RATE: float
    MAX_POWER: int
    MAX_BUFFER_ENERGY: int
    MAX_CHASSIS_ENERGY: int

    def get_connection_status(self) -> str:
        """获取连接状态"""
        return "已连接" if self.CONNECTION_STATE == 1 else "未连接"

    def get_field_status(self) -> str:
        """获取场地状态"""
        return "已上场" if self.FIELD_STATE == 1 else "未上场"

    def get_shooter_mode_name(self) -> str:
        """获取发射机构性能体系名称"""
        shooter_modes = {
            1: "冷却优先",
            2: "爆发优先",
            3: "英雄近战优先",
            4: "英雄远程优先"
        }
        return shooter_modes.get(self.PERFORMANCE_SYSTEM_SHOOTER, "未知")

    def get_chassis_mode_name(self) -> str:
        """获取底盘性能体系名称"""
        chassis_modes = {
            1: "血量优先",
            2: "功率优先",
            3: "英雄近战优先",
            4: "英雄远程优先"
        }
        return chassis_modes.get(self.PERFORMANCE_SYSTEM_CHASSIS, "未知")


@dataclass
class RMDynamic:
    """
    机器人实时数据
    目前包含：当前血量、当前热量、上一次弹丸射速、当前剩余底盘能量、当前缓冲能量、
    当前经验值、距离下一次升级仍需获得的经验、累计已发弹量、剩余允许发弹量、
    是否处于脱战状态、脱战状态倒计时、是否可以远程补血、是否可以远程补弹等
    """
    CURRENT_HEALTH: int
    CURRENT_HEAT: float
    LAST_PROJECTILE_FIRE_RATE: float
    CURRENT_CHASSIS_ENERGY: int
    CURRENT_BUFFER_ENERGY: int
    CURRENT_EXPERIENCE: int
    EXPERIENCE_FOR_UPGRADE: int
    TOTAL_PROJECTILES_FIRED: int
    REMAINING_AMMO: int
    IS_OUT_OF_COMBAT: bool
    OUT_OF_COMBAT_COUNTDOWN: int
    CAN_REMOTE_HEAL: bool
    CAN_REMOTE_AMMO: bool


@dataclass
class RMPosition:
    """
    机器人空间坐标和朝向
    目前包含：世界坐标 X/Y/Z 轴、朝向角度
    """
    X: float
    Y: float
    Z: float
    YAW: float


@dataclass
class RMBuff:
    """
    Buff 效果信息
    目前包含：机器人 ID、Buff 类型、Buff 增益值、Buff 最大剩余时间、Buff 剩余时间
    """
    ROBOT_ID: int
    BUFF_TYPE: Literal[1, 2, 3, 4, 5, 6, 7]
    BUFF_LEVEL: int
    BUFF_MAX_TIME: int
    BUFF_LEFT_TIME: int

    def get_buff_type_name(self) -> str:
        """获取 Buff 类型名称"""
        buff_types = {
            1: "攻击增益",
            2: "防御增益",
            3: "射击热量冷却增益",
            4: "底盘功率增益",
            5: "回血增益",
            6: "可兑换允许发弹量",
            7: "地形跨越增益（预备）"
        }
        return buff_types.get(self.BUFF_TYPE, "未知 Buff")


@dataclass
class RMPenalty:
    """
    判罚信息
    目前包含：当前受罚类型、当前受罚效果时长、当前判罚数量
    """
    PENALTY_TYPE: Literal[1, 2, 3, 4, 5, 6]
    PENALTY_EFFECT_SEC: int
    TOTAL_PENALTY_NUM: int

    def get_penalty_type_name(self) -> str:
        """获取判罚类型名称"""
        penalty_types = {
            1: "黄牌",
            2: "双方黄牌",
            3: "红牌",
            4: "超功率",
            5: "超热量",
            6: "超射速"
        }
        return penalty_types.get(self.PENALTY_TYPE, "未知判罚")


@dataclass
class RMPathPlan:
    """
    哨兵轨迹规划信息
    目前包含：哨兵意图、起始点坐标、X/Y 增量数组、发送者 ID
    """
    INTENTION: Literal[1, 2, 3]  # 1=攻击, 2=防守, 3=移动
    START_POS_X: int
    START_POS_Y: int
    OFFSET_X: list[int]  # 相对起始点 X 增量数组（-128~+127, 长度 49）
    OFFSET_Y: list[int]  # 相对起始点 Y 增量数组（-128~+127, 长度 49）
    SENDER_ID: int

    def get_intention_name(self) -> str:
        """获取意图名称"""
        intentions = {
            1: "攻击",
            2: "防守",
            3: "移动"
        }
        return intentions.get(self.INTENTION, "未知意图")


@dataclass
class RMRadar:
    """
    雷达发送的机器人位置信息
    目前包含：目标机器人 ID、目标位置 X/Y、朝向角度、是否特殊标识
    """
    TARGET_ROBOT_ID: int
    TARGET_POS_X: float
    TARGET_POS_Y: float
    TORWARD_ANGLE: float
    IS_HIGH_LIGHT: Literal[0, 1, 2]  # 0=否; 1=是; 2=是，但目标机器人此时定位模块为离线状态


@dataclass
class RMModuleStatus:
    """
    机器人各模块运行状态
    目前包含：电源管理模块、RFID 模块、灯条模块、17mm 发射机构、42mm 发射机构、
    定位模块、装甲模块、图传模块、电容模块、主控、激光检测模块
    每个模块状态：0=离线，1=在线，2=因安装不规范被视为离线
    """
    POWER_MANAGER: Literal[0, 1, 2]
    RFID: Literal[0, 1, 2]
    LIGHT_STRIP: Literal[0, 1, 2]
    SMALL_SHOOTER: Literal[0, 1, 2]
    BIG_SHOOTER: Literal[0, 1, 2]
    UWB: Literal[0, 1, 2]
    ARMOR: Literal[0, 1, 2]
    VIDEO_TRANSMISSION: Literal[0, 1, 2]
    CAPACITOR: Literal[0, 1, 2]
    MAIN_CONTROLLER: Literal[0, 1, 2]
    LASER_DETECTION_MODULE: Literal[0, 1, 2]

    def get_module_status_name(self, status: int) -> str:
        """获取模块状态名称"""
        status_names = {
            0: "离线",
            1: "在线",
            2: "因安装不规范被视为离线"
        }
        return status_names.get(status, "未知状态")


@dataclass
class RMSentryStatus:
    """
    哨兵姿态和弱化状态
    目前包含：姿态 ID、是否弱化
    """
    posture_id: Literal[1, 2, 3]  # 1=进攻姿态, 2=防御姿态, 3=移动姿态
    is_weakened: bool

    def get_posture_name(self) -> str:
        """获取姿态名称"""
        postures = {
            1: "进攻姿态",
            2: "防御姿态",
            3: "移动姿态"
        }
        return postures.get(self.posture_id, "未知姿态")


@dataclass
class RMDartStatus:
    """
    飞镖目标选择状态
    目前包含：目标 ID、闸门状态
    """
    TARGET_ID: Literal[1, 2, 3, 4, 5]  # 1=前哨站, 2=基地固定目标, 3=基地随机固定目标, 4=基地随机移动目标, 5=基地末端移动目标
    OPEN: Literal[0, 1, 2]  # 0=关闭, 1=开启中, 2=已开启

    def get_gate_status_name(self) -> str:
        """获取闸门状态名称"""
        status_names = {
            0: "关闭",
            1: "开启中",
            2: "已开启"
        }
        return status_names.get(self.OPEN, "未知状态")


@dataclass
class RMAirSupportStatus:
    """
    空中支援状态
    目前包含：空中支援状态、免费空中支援剩余时间、付费空中支援已花费金币、
    当前激光检测模块是否正在检测到被照射、空中机器人被反制状态
    """
    AIRSUPPORT_STATUS: Literal[0, 1]  # 0=未进行空中支援, 1=正在空中支援
    LEFT_TIME: int
    COST_COINS: int
    IS_BEING_TARGETED: Literal[0, 1]  # 0=未被照射, 1=被照射
    SHOOTER_STATUS: Literal[0, 1]  # 0=发射机构因雷达反制而被锁定, 1=发射机构正常，未被反制

    def get_airsupport_status_name(self) -> str:
        """获取空中支援状态名称"""
        status_names = {
            0: "未进行空中支援",
            1: "正在空中支援"
        }
        return status_names.get(self.AIRSUPPORT_STATUS, "未知状态")


@dataclass
class RMPerformanceSelection:
    """
    性能体系状态
    目前包含：发射机构性能体系、底盘性能体系、哨兵控制方式
    """
    SHOOTER: Literal[1, 2, 3, 4]  # 性能体系枚举值同 RobotStaticStatus
    CHASSIS: Literal[1, 2, 3, 4]
    SENTRY_CONTROL: Literal[0, 1]  # 0=哨兵自动控制, 1=哨兵半自动控制

    def get_shooter_mode_name(self) -> str:
        """获取发射机构性能体系名称"""
        shooter_modes = {
            1: "冷却优先",
            2: "爆发优先",
            3: "英雄近战优先",
            4: "英雄远程优先"
        }
        return shooter_modes.get(self.SHOOTER, "未知")

    def get_chassis_mode_name(self) -> str:
        """获取底盘性能体系名称"""
        chassis_modes = {
            1: "血量优先",
            2: "功率优先",
            3: "英雄近战优先",
            4: "英雄远程优先"
        }
        return chassis_modes.get(self.CHASSIS, "未知")


@dataclass
class RMDeployModeStatus:
    """
    部署模式状态
    目前包含：当前部署模式状态
    """
    STATUS: Literal[0, 1]  # 0=未部署, 1=已部署

    def get_status_name(self) -> str:
        """获取部署模式状态名称"""
        status_names = {
            0: "未部署",
            1: "已部署"
        }
        return status_names.get(self.STATUS, "未知状态")


@dataclass
class RMRuneStatus:
    """
    能量机关状态
    目前包含：当前能量机关状态枚举、当前已激活的灯臂数量、总环数
    """
    RUNE_STATUS: Literal[1, 2, 3]  # 1=未激活, 2=正在激活, 3=已激活
    ACTIVATED_ARMS: int
    AVERAGE_RINGS: int

    def get_rune_status_name(self) -> str:
        """获取能量机关状态名称"""
        status_names = {
            1: "未激活",
            2: "正在激活",
            3: "已激活"
        }
        return status_names.get(self.RUNE_STATUS, "未知状态")


@dataclass
class RMTechCoreMotion:
    """
    科技核心运动状态
    目前包含：当前可选择的最高装配难度等级、科技核心状态、
    对方科技核心状态、己方装配总剩余时长、己方单个步骤装配间隔剩余时长
    """
    MAXIMUM_DIFFICULTY_LEVEL: int
    STATUS: Literal[1, 2, 3, 4, 5, 6]  # 1=未进入装配状态, 2=已选择装配难度，科技核心移动中, 3=科技核心移动完成，可进行首个装配步骤, 4=上一个装配步骤已完成，可进行下一个装配步骤, 5=装配步骤已全部完成, 6=已确认装配，科技核心移动中
    ENEMY_CORE_STATUS: Literal[0, 1, 2]  # 0=对方没有正在装配, 1=对方正在装配非四级难度, 2=对方正在装配四级难度
    REMAIN_TIME_ALL: int
    REMAIN_TIME_STEP: int

    def get_status_name(self) -> str:
        """获取科技核心状态名称"""
        status_names = {
            1: "未进入装配状态",
            2: "已选择装配难度，科技核心移动中",
            3: "科技核心移动完成，可进行首个装配步骤",
            4: "上一个装配步骤已完成，可进行下一个装配步骤",
            5: "装配步骤已全部完成",
            6: "已确认装配，科技核心移动中"
        }
        return status_names.get(self.STATUS, "未知状态")





# ============================================================
# 状态机
# ============================================================
class RMClientStates:
    """
    比赛全局状态存储。
    所有字段以嵌套字典形式管理，支持直接被 JSON 序列化后通过 HTTP 推送给前端。
    根据通信协议文档定义所有从服务器同步的字段。
    """

    def __init__(self, ally_color: Optional[str] = None) -> None:
        self.updates: Dict[str, Any] = {
            # GameStatus: 同步比赛全局状态信息 (5Hz)
            "GameStatus": {
                "current_round": 0,
                "total_rounds": 0,
                "red_score": 0,
                "blue_score": 0,
                "current_stage": 0,
                "stage_countdown_sec": 0,
                "stage_elapsed_sec": 0,
                "is_paused": False,
            },
            
            # GlobalUnitStatus: 同步基地、前哨站和所有机器人状态 (1Hz)
            "GlobalUnitStatus": {
                "base_health": 0,
                "base_status": 0,
                "base_shield": 0,
                "outpost_health": 0,
                "outpost_status": 0,
                "enemy_base_health": 0,
                "enemy_base_status": 0,
                "enemy_base_shield": 0,
                "enemy_outpost_health": 0,
                "enemy_outpost_status": 0,
                "robot_health": [],
                "robot_bullets": [],
                "total_damage_ally": 0,
                "total_damage_enemy": 0,
            },
            
            # GlobalLogisticsStatus: 同步全局后勤信息 (1Hz)
            "GlobalLogisticsStatus": {
                "remaining_economy": 0,
                "total_economy_obtained": 0,
                "tech_level": 0,
                "encryption_level": 0,
            },
            
            # GlobalSpecialMechanism: 同步正在生效的全局特殊机制 (1Hz)
            "GlobalSpecialMechanism": {
                "mechanism_id": [],
                "mechanism_time_sec": [],
            },
            
            # Event: 全局事件通知 (触发式发送)
            "Event": {
                "event_id": 0,
                "param": "",
            },
            
            # RobotInjuryStat: 机器人一次存活期间累计受伤统计 (1Hz)
            "RobotInjuryStat": {
                "total_damage": 0,
                "collision_damage": 0,
                "small_projectile_damage": 0,
                "large_projectile_damage": 0,
                "dart_splash_damage": 0,
                "module_offline_damage": 0,
                "offline_damage": 0,
                "penalty_damage": 0,
                "server_kill_damage": 0,
                "killer_id": 0,
            },
            
            # RobotRespawnStatus: 机器人复活状态同步 (1Hz)
            "RobotRespawnStatus": {
                "is_pending_respawn": False,
                "total_respawn_progress": 0,
                "current_respawn_progress": 0,
                "can_free_respawn": False,
                "gold_cost_for_respawn": 0,
                "can_pay_for_respawn": False,
            },
            
            # RobotStaticStatus: 机器人固定属性和配置 (1Hz)
            "RobotStaticStatus": {
                "connection_state": 0,
                "field_state": 0,
                "alive_state": 0,
                "robot_id": 0,
                "robot_type": 0,
                "performance_system_shooter": 1,
                "performance_system_chassis": 1,
                "level": 0,
                "max_health": 0,
                "max_heat": 0,
                "heat_cooldown_rate": 0.0,
                "max_power": 0,
                "max_buffer_energy": 0,
                "max_chassis_energy": 0,
            },
            
            # RobotDynamicStatus: 机器人实时数据 (10Hz)
            "RobotDynamicStatus": {
                "CURRENT_HEALTH": 0,
                "CURRENT_HEAT": 0.0,
                "LAST_PROJECTILE_FIRE_RATE": 0.0,
                "CURRENT_CHASSIS_ENERGY": 0,
                "CURRENT_BUFFER_ENERGY": 0,
                "CURRENT_EXPERIENCE": 0,
                "EXPERIENCE_FOR_UPGRADE": 0,
                "TOTAL_PROJECTILES_FIRED": 0,
                "REMAINING_AMMO": 0,
                "IS_OUT_OF_COMBAT": False,
                "OUT_OF_COMBAT_COUNTDOWN": 0,
                "CAN_REMOTE_HEAL": False,
                "CAN_REMOTE_AMMO": False,
            },
            
            # RobotModuleStatus: 机器人各模块运行状态 (1Hz)
            "RobotModuleStatus": {
                "POWER_MANAGER": 0,
                "RFID": 0,
                "LIGHT_STRIP": 0,
                "SMALL_SHOOTER": 0,
                "BIG_SHOOTER": 0,
                "UWB": 0,
                "ARMOR": 0,
                "VIDEO_TRANSMISSION": 0,
                "CAPACITOR": 0,
                "MAIN_CONTROLLER": 0,
                "LASER_DETECTION_MODULE": 0,
            },
            
            # RobotPosition: 机器人空间坐标和朝向 (1Hz)
            "RobotPosition": {
                "X": 0.0,
                "Y": 0.0,
                "Z": 0.0,
                "YAW": 0.0,
            },
            
            # Buff: Buff 效果信息 (获得增益时触发发送，此后 1Hz 定频发送)
            "Buff": {
                "ROBOT_ID": 0,
                "BUFF_TYPE": 0,
                "BUFF_LEVEL": 0,
                "BUFF_MAX_TIME": 0,
                "BUFF_LEFT_TIME": 0,
            },
            
            # PenaltyInfo: 判罚信息同步 (触发式发送)
            "PenaltyInfo": {
                "PENALTY_TYPE": 0,
                "PENALTY_EFFECT_SEC": 0,
                "TOTAL_PENALTY_NUM": 0,
            },
            
            # RobotPathPlanInfo: 哨兵轨迹规划信息 (1Hz)
            "RobotPathPlanInfo": {
                "INTENTION": 0,
                "START_POS_X": 0,
                "START_POS_Y": 0,
                "OFFSET_X": [],
                "OFFSET_Y": [],
                "SENDER_ID": 0,
            },
            
            # RadarInfoToClient: 雷达发送的机器人位置信息 (1Hz)
            "RadarInfoToClient": {
                "TARGET_ROBOT_ID": 0,
                "TARGET_POS_X": 0.0,
                "TARGET_POS_Y": 0.0,
                "TORWARD_ANGLE": 0.0,
                "IS_HIGH_LIGHT": 0,
            },
            
            # TechCoreMotionStateSync: 科技核心运动状态同步 (1Hz)
            "TechCoreMotionStateSync": {
                "MAXIMUM_DIFFICULTY_LEVEL": 0,
                "STATUS": 0,
                "ENEMY_CORE_STATUS": 0,
                "REMAIN_TIME_ALL": 0,
                "REMAIN_TIME_STEP": 0,
            },
            
            # RobotPerformanceSelectionSync: 步兵/英雄性能体系状态同步 (1Hz)
            "RobotPerformanceSelectionSync": {
                "SHOOTER": 1,
                "CHASSIS": 1,
                "SENTRY_CONTROL": 0,
            },
            
            # DeployModeStatusSync: 英雄部署模式状态同步 (1Hz)
            "DeployModeStatusSync": {
                "STATUS": 0,
            },
            
            # RuneStatusSync: 能量机关状态同步 (1Hz)
            "RuneStatusSync": {
                "RUNE_STATUS": 1,
                "ACTIVATED_ARMS": 0,
                "AVERAGE_RINGS": 0,
            },
            
            # SentryStatusSync: 哨兵姿态和弱化状态 (1Hz)
            "SentryStatusSync": {
                "POSTURE_ID": 1,
                "IS_WEAKENED": False,
            },
            
            # DartSelectTargetStatusSync: 飞镖目标选择状态同步 (1Hz)
            "DartSelectTargetStatusSync": {
                "TARGET_ID": 1,
                "OPEN": 0,
            },
            
            # AirSupportStatusSync: 空中支援状态反馈 (1Hz)
            "AirSupportStatusSync": {
                "AIRSUPPORT_STATUS": 0,
                "LEFT_TIME": 0,
                "COST_COINS": 0,
                "IS_BEING_TARGETED": 0,
                "SHOOTER_STATUS": 1,
            },
        }

        self.side2color: Dict[str, str] = {ALLY: UNKNOWN, ENEMY: UNKNOWN}
        self.color2side: Dict[str, str] = {RED: UNKNOWN, BLUE: UNKNOWN}

        if ally_color is not None:
            self.set_ally_color(ally_color)

    # --------------------------------------------------------
    # 阵营映射
    # --------------------------------------------------------
    def set_ally_color(self, color: str) -> None:
        """设置己方颜色，自动更新双向映射。"""
        if color == RED:
            self.side2color[ALLY] = RED
            self.side2color[ENEMY] = BLUE
            self.color2side[RED] = ALLY
            self.color2side[BLUE] = ENEMY
        elif color == BLUE:
            self.side2color[ALLY] = BLUE
            self.side2color[ENEMY] = RED
            self.color2side[BLUE] = ALLY
            self.color2side[RED] = ENEMY
        else:
            raise ValueError("Invalid color. Use 'RED' or 'BLUE'.")

    @property
    def ally_color(self) -> str:
        return self.side2color[ALLY]

    @property
    def enemy_color(self) -> str:
        return self.side2color[ENEMY]
    
    @property
    def red_side(self) -> str:
        return self.color2side[RED]
    
    @property
    def blue_side(self) -> str:
        return self.color2side[BLUE]

    # --------------------------------------------------------
    # 状态读写
    # --------------------------------------------------------
    def update(self, data: Dict[str, Any]) -> None:
        """
        批量更新状态字段。
        仅支持嵌套格式: {"GameStatus": {"red_score": 100, "blue_score": 50}}
        内部以嵌套字典形式存储，支持深度更新。
        """
        for key, value in data.items():
            if isinstance(value, dict):
                # 嵌套格式: {"GameStatus": {...}}
                # 深度更新，保留其他字段
                if key not in self.updates:
                    self.updates[key] = {}
                elif not isinstance(self.updates[key], dict):
                    # 如果目标不是字典，创建新字典
                    self.updates[key] = {}
                
                # 更新嵌套字段
                self.updates[key].update(value)
            else:
                # 嵌套格式的第一层不能直接赋值，必须用字典
                raise ValueError(f"Invalid update format. Field '{key}' must use nested format: {{'{key}': {{...}}}}")

    def get(self, key: str, default: Any = 0) -> Any:
        """
        获取状态字段值。
        支持 "GameStatus.red_score" 形式的访问。
        """
        if "." in key:
            # 嵌套访问: "GameStatus.red_score"
            parts = key.split(".")
            current = self.updates
            for part in parts[:-1]:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return default
            if isinstance(current, dict) and parts[-1] in current:
                return current[parts[-1]]
            return default
        else:
            # 直接访问: "GameStatus"
            return self.updates.get(key, default)

    def to_dict(self) -> Dict[str, Any]:
        """
        导出完整状态快照（含阵营元数据），
        可直接 JSON 序列化发送给前端。
        """
        return {
            "ally_color": self.ally_color,
            "enemy_color": self.enemy_color,
            "states": self.updates,
        }

    # --------------------------------------------------------
    # 便捷查询
    # --------------------------------------------------------
    def get_time(self) -> RMTime:
        """获取时间对象，从 GameStatus 嵌套结构中读取"""
        game_status = self.updates.get("GameStatus", {})
        return RMTime(
            REMAINING_TIME=game_status.get("stage_countdown_sec", 0),
            PASSED_TIME=game_status.get("stage_elapsed_sec", 0),
            TOTAL_TIME=TOTAL_TIME,
        )

    def get_score(self) -> RMScore:
        """返回: 红方得分/蓝方得分，从 GameStatus 嵌套结构中读取"""
        game_status = self.updates.get("GameStatus", {})
        red = game_status.get("red_score", 0)
        blue = game_status.get("blue_score", 0)
        return RMScore(RED=red, BLUE=blue)

    def get_building_status(
        self, side: str = ALL_SIDES, building_type: str = ALL_BUILDINGS
    ) -> RMAllBuildingsStatus | RMBuildingStatus | RMBaseStatus | RMOutpostStatus:
        """
        返回建筑状态，支持按阵营/建筑类型筛选。
        内部自动处理己方/敌方的颜色映射。
        从 GlobalUnitStatus 嵌套结构中读取数据。
        """
        ally_color = self.side2color[ALLY]
        enemy_color = self.side2color[ENEMY]

        def make_side(is_ally: bool) -> RMBuildingStatus:
            prefix = "" if is_ally else "enemy_"
            unit_status = self.updates.get("GlobalUnitStatus", {})
            return RMBuildingStatus(
                BASE=RMBaseStatus(
                    HEALTH=unit_status.get(f"{prefix}base_health", 0),
                    STATUS=unit_status.get(f"{prefix}base_status", 0),
                    SHIELD=unit_status.get(f"{prefix}base_shield", 0),
                ),
                OUTPOST=RMOutpostStatus(
                    HEALTH=unit_status.get(f"{prefix}outpost_health", 0),
                    STATUS=unit_status.get(f"{prefix}outpost_status", 0),
                    SHIELD=unit_status.get(f"{prefix}outpost_shield", 0),
                )
            )

        ally_side = make_side(is_ally=True)
        enemy_side = make_side(is_ally=False)

        building_status = RMAllBuildingsStatus(
            RED=ally_side if ally_color == RED else enemy_side,
            BLUE=ally_side if ally_color == BLUE else enemy_side,
        )

        if side == ALL_SIDES:
            assert building_type == ALL_BUILDINGS, \
                "当 side 为 ALL_SIDES 时，building_type 必须为 ALL_BUILDINGS"
            return building_status

        assert side in (RED, BLUE), \
            "Invalid side. Use 'RED', 'BLUE' or 'ALL_SIDES'."

        if building_type == ALL_BUILDINGS:
            return getattr(building_status, side)
        assert building_type in (BASE, OUTPOST), \
            "Invalid building_type. Use 'BASE', 'OUTPOST' or 'ALL_BUILDINGS'."
        return getattr(getattr(building_status, side), building_type)

    def get_all_health(self):
        """
        获取所有机器人血量
        从 GlobalUnitStatus.robot_health 中读取
        """
        unit_status = self.updates.get("GlobalUnitStatus", {})
        raw_health_mes = unit_status.get("robot_health")
        return raw_health_mes
    
    def get_ally_bullets(self):
        """
        获取己方弹药数量
        从 GlobalUnitStatus.robot_bullets 中读取
        """
        unit_status = self.updates.get("GlobalUnitStatus", {})
        raw_bullets_mes = unit_status.get("robot_bullets")
        return raw_bullets_mes
    
    def get_damage(self) -> RMDamage:
        """
        获取伤害数据
        从 GlobalUnitStatus 中读取己方和敌方累计总伤害
        """
        unit_status = self.updates.get("GlobalUnitStatus", {})
        ally_damage = unit_status.get("total_damage_ally", 0)
        enemy_damage = unit_status.get("total_damage_enemy", 0)
        damage_info = RMDamage(ALLY=ally_damage, ENEMY=enemy_damage)
        return damage_info
    
    def get_ally_economy(self) -> RMEconomy:
        """
        获取己方经济数据
        从 GlobalLogisticsStatus 嵌套结构中读取
        """
        logistics_status = self.updates.get("GlobalLogisticsStatus", {})
        remaining = logistics_status.get("remaining_economy", 0)
        total = logistics_status.get("total_economy_obtained", 0)
        return RMEconomy(ALLY=remaining, ALLY_ALL=total)

    def get_ally_level(self) -> RMLevel:
        """
        获取己方等级数据
        从 GlobalLogisticsStatus 嵌套结构中读取
        """
        tech_level = self.get("GlobalTechStatus.tech_level")
        encr_level = self.get("GlobalTechStatus.encryption_level")
        # level = tech_level + encr_level
        return RMLevel(TECH_LEVEL=tech_level, ENCRYPTION_LEVEL=encr_level)

    def get_special_mechanism(self) -> RMMec:
        return RMMec(
            MEC_ID=self.get("GlobalSpecialMechanism.mechanism_id"),
            MEC_TIME=self.get("GlobalSpecialMechanism.mechanism_time_sec"),
        )

    def get_event(self) -> RMEvent:
        """
        获取事件信息
        从 Event 嵌套结构中读取
        """
        event = self.updates.get("Event", {})
        return RMEvent(
            EVENT_ID=event.get("event_id", 0),
            PARAMS=event.get("param", ""),
        )

    def get_injury(self) -> RMInjury:
        """
        获取机器人受伤统计信息
        从 RobotInjuryStat 嵌套结构中读取
        """
        injury = self.updates.get("RobotInjuryStat", {})
        return RMInjury(
            TOTAL_DAMAGE=injury.get("total_damage", 0),
            COLLISION_DAMAGE=injury.get("collision_damage", 0),
            SMALL_PROJECTILE_DAMAGE=injury.get("small_projectile_damage", 0),
            LARGE_PROJECTILE_DAMAGE=injury.get("large_projectile_damage", 0),
            DART_SPLASH_DAMAGE=injury.get("dart_splash_damage", 0),
            MODULE_OFFLINE_DAMAGE=injury.get("module_offline_damage", 0),
            OFFLINE_DAMAGE=injury.get("offline_damage", 0),
            PENALTY_DAMAGE=injury.get("penalty_damage", 0),
            SERVER_KILL_DAMAGE=injury.get("server_kill_damage", 0),
            KILLER_ID=injury.get("killer_id", 0),
        )

    def get_respawn(self) -> RMRepawn:
        """
        获取机器人重生信息
        从 RobotRespawnStatus 嵌套结构中读取
        """
        respawn = self.updates.get("RobotRespawnStatus", {})
        return RMRepawn(
            is_pending_respawn=respawn.get("is_pending_respawn", False),
            total_respawn_progress=respawn.get("total_respawn_progress", 0),
            current_respawn_progress=respawn.get("current_respawn_progress", 0),
            can_free_respawn=respawn.get("can_free_respawn", False),
            gold_cost_for_respawn=respawn.get("gold_cost_for_respawn", 0),
            can_pay_for_respawn=respawn.get("can_pay_for_respawn", False),
        )

    def get_static_status(self) -> RMStatic:
        """
        获取机器人静态属性
        从 RobotStaticStatus 嵌套结构中读取
        """
        static = self.updates.get("RobotStaticStatus", {})
        return RMStatic(
            CONNECTION_STATE=static.get("connection_state", 0),
            FIELD_STATE=static.get("field_state", 0),
            ALIVE_STATE=static.get("alive_state", 0),
            ROBOT_ID=static.get("robot_id", 0),
            ROBOT_TYPE=static.get("robot_type", 0),
            PERFORMANCE_SYSTEM_SHOOTER=static.get("performance_system_shooter", 1),
            PERFORMANCE_SYSTEM_CHASSIS=static.get("performance_system_chassis", 1),
            LEVEL=static.get("level", 0),
            MAX_HEALTH=static.get("max_health", 0),
            MAX_HEAT=static.get("max_heat", 0),
            HEAT_COOLDOWN_RATE=static.get("heat_cooldown_rate", 0.0),
            MAX_POWER=static.get("max_power", 0),
            MAX_BUFFER_ENERGY=static.get("max_buffer_energy", 0),
            MAX_CHASSIS_ENERGY=static.get("max_chassis_energy", 0),
        )

    def get_dynamic_status(self) -> RMDynamic:
        """
        获取机器人实时数据
        从 RobotDynamicStatus 嵌套结构中读取
        """
        dynamic = self.updates.get("RobotDynamicStatus", {})
        return RMDynamic(
            CURRENT_HEALTH=dynamic.get("CURRENT_HEALTH", 0),
            CURRENT_HEAT=dynamic.get("CURRENT_HEAT", 0.0),
            LAST_PROJECTILE_FIRE_RATE=dynamic.get("LAST_PROJECTILE_FIRE_RATE", 0.0),
            CURRENT_CHASSIS_ENERGY=dynamic.get("CURRENT_CHASSIS_ENERGY", 0),
            CURRENT_BUFFER_ENERGY=dynamic.get("CURRENT_BUFFER_ENERGY", 0),
            CURRENT_EXPERIENCE=dynamic.get("CURRENT_EXPERIENCE", 0),
            EXPERIENCE_FOR_UPGRADE=dynamic.get("EXPERIENCE_FOR_UPGRADE", 0),
            TOTAL_PROJECTILES_FIRED=dynamic.get("TOTAL_PROJECTILES_FIRED", 0),
            REMAINING_AMMO=dynamic.get("REMAINING_AMMO", 0),
            IS_OUT_OF_COMBAT=dynamic.get("IS_OUT_OF_COMBAT", False),
            OUT_OF_COMBAT_COUNTDOWN=dynamic.get("OUT_OF_COMBAT_COUNTDOWN", 0),
            CAN_REMOTE_HEAL=dynamic.get("CAN_REMOTE_HEAL", False),
            CAN_REMOTE_AMMO=dynamic.get("CAN_REMOTE_AMMO", False),
        )

    def get_module_status(self) -> RMModuleStatus:
        """
        获取机器人各模块运行状态
        从 RobotModuleStatus 嵌套结构中读取
        """
        module = self.updates.get("RobotModuleStatus", {})
        return RMModuleStatus(
            POWER_MANAGER=module.get("POWER_MANAGER", 0),
            RFID=module.get("RFID", 0),
            LIGHT_STRIP=module.get("LIGHT_STRIP", 0),
            SMALL_SHOOTER=module.get("SMALL_SHOOTER", 0),
            BIG_SHOOTER=module.get("BIG_SHOOTER", 0),
            UWB=module.get("UWB", 0),
            ARMOR=module.get("ARMOR", 0),
            VIDEO_TRANSMISSION=module.get("VIDEO_TRANSMISSION", 0),
            CAPACITOR=module.get("CAPACITOR", 0),
            MAIN_CONTROLLER=module.get("MAIN_CONTROLLER", 0),
            LASER_DETECTION_MODULE=module.get("LASER_DETECTION_MODULE", 0),
        )

    def get_position(self) -> RMPosition:
        """
        获取机器人空间坐标和朝向
        从 RobotPosition 嵌套结构中读取
        """
        position = self.updates.get("RobotPosition", {})
        return RMPosition(
            X=position.get("X", 0.0),
            Y=position.get("Y", 0.0),
            Z=position.get("Z", 0.0),
            YAW=position.get("YAW", 0.0),
        )

    def get_buff(self) -> RMBuff:
        """
        获取Buff效果信息
        从 Buff 嵌套结构中读取
        """
        buff = self.updates.get("Buff", {})
        return RMBuff(
            ROBOT_ID=buff.get("ROBOT_ID", 0),
            BUFF_TYPE=buff.get("BUFF_TYPE", 0),
            BUFF_LEVEL=buff.get("BUFF_LEVEL", 0),
            BUFF_MAX_TIME=buff.get("BUFF_MAX_TIME", 0),
            BUFF_LEFT_TIME=buff.get("BUFF_LEFT_TIME", 0),
        )

    def get_penalty(self) -> RMPenalty:
        """
        获取判罚信息
        从 PenaltyInfo 嵌套结构中读取
        """
        penalty = self.updates.get("PenaltyInfo", {})
        return RMPenalty(
            PENALTY_TYPE=penalty.get("PENALTY_TYPE", 0),
            PENALTY_EFFECT_SEC=penalty.get("PENALTY_EFFECT_SEC", 0),
            TOTAL_PENALTY_NUM=penalty.get("TOTAL_PENALTY_NUM", 0),
        )

    def get_path_plan(self) -> RMPathPlan:
        """
        获取哨兵轨迹规划信息
        从 RobotPathPlanInfo 嵌套结构中读取
        """
        path_plan = self.updates.get("RobotPathPlanInfo", {})
        return RMPathPlan(
            INTENTION=path_plan.get("INTENTION", 0),
            START_POS_X=path_plan.get("START_POS_X", 0),
            START_POS_Y=path_plan.get("START_POS_Y", 0),
            OFFSET_X=path_plan.get("OFFSET_X", []),
            OFFSET_Y=path_plan.get("OFFSET_Y", []),
            SENDER_ID=path_plan.get("SENDER_ID", 0),
        )

    def get_radar(self) -> RMRadar:
        """
        获取雷达发送的机器人位置信息
        从 RadarInfoToClient 嵌套结构中读取
        """
        radar = self.updates.get("RadarInfoToClient", {})
        return RMRadar(
            TARGET_ROBOT_ID=radar.get("TARGET_ROBOT_ID", 0),
            TARGET_POS_X=radar.get("TARGET_POS_X", 0.0),
            TARGET_POS_Y=radar.get("TARGET_POS_Y", 0.0),
            TORWARD_ANGLE=radar.get("TORWARD_ANGLE", 0.0),
            IS_HIGH_LIGHT=radar.get("IS_HIGH_LIGHT", 0),
        )

    def get_tech_core_motion(self) -> RMTechCoreMotion:
        """
        获取科技核心运动状态
        从 TechCoreMotionStateSync 嵌套结构中读取
        """
        tech_core = self.updates.get("TechCoreMotionStateSync", {})
        return RMTechCoreMotion(
            MAXIMUM_DIFFICULTY_LEVEL=tech_core.get("MAXIMUM_DIFFICULTY_LEVEL", 0),
            STATUS=tech_core.get("STATUS", 0),
            ENEMY_CORE_STATUS=tech_core.get("ENEMY_CORE_STATUS", 0),
            REMAIN_TIME_ALL=tech_core.get("REMAIN_TIME_ALL", 0),
            REMAIN_TIME_STEP=tech_core.get("REMAIN_TIME_STEP", 0),
        )

    def get_performance_selection(self) -> RMPerformanceSelection:
        """
        获取性能体系状态
        从 RobotPerformanceSelectionSync 嵌套结构中读取
        """
        performance = self.updates.get("RobotPerformanceSelectionSync", {})
        return RMPerformanceSelection(
            SHOOTER=performance.get("SHOOTER", 1),
            CHASSIS=performance.get("CHASSIS", 1),
            SENTRY_CONTROL=performance.get("SENTRY_CONTROL", 0),
        )

    def get_deploy_mode_status(self) -> RMDeployModeStatus:
        """
        获取部署模式状态
        从 DeployModeStatusSync 嵌套结构中读取
        """
        deploy_mode = self.updates.get("DeployModeStatusSync", {})
        return RMDeployModeStatus(
            STATUS=deploy_mode.get("STATUS", 0),
        )

    def get_rune_status(self) -> RMRuneStatus:
        """
        获取能量机关状态
        从 RuneStatusSync 嵌套结构中读取
        """
        rune = self.updates.get("RuneStatusSync", {})
        return RMRuneStatus(
            RUNE_STATUS=rune.get("RUNE_STATUS", 1),
            ACTIVATED_ARMS=rune.get("ACTIVATED_ARMS", 0),
            AVERAGE_RINGS=rune.get("AVERAGE_RINGS", 0),
        )

    def get_sentry_status(self) -> RMSentryStatus:
        """
        获取哨兵姿态和弱化状态
        从 SentryStatusSync 嵌套结构中读取
        """
        sentry = self.updates.get("SentryStatusSync", {})
        return RMSentryStatus(
            posture_id=sentry.get("POSTURE_ID", 1),
            is_weakened=sentry.get("IS_WEAKENED", False),
        )

    def get_dart_status(self) -> RMDartStatus:
        """
        获取飞镖目标选择状态
        从 DartSelectTargetStatusSync 嵌套结构中读取
        """
        dart = self.updates.get("DartSelectTargetStatusSync", {})
        return RMDartStatus(
            TARGET_ID=dart.get("TARGET_ID", 1),
            OPEN=dart.get("OPEN", 0),
        )

    def get_airsupport_status(self) -> RMAirSupportStatus:
        """
        获取空中支援状态
        从 AirSupportStatusSync 嵌套结构中读取
        """
        airsupport = self.updates.get("AirSupportStatusSync", {})
        return RMAirSupportStatus(
            AIRSUPPORT_STATUS=airsupport.get("AIRSUPPORT_STATUS", 0),
            LEFT_TIME=airsupport.get("LEFT_TIME", 0),
            COST_COINS=airsupport.get("COST_COINS", 0),
            IS_BEING_TARGETED=airsupport.get("IS_BEING_TARGETED", 0),
            SHOOTER_STATUS=airsupport.get("SHOOTER_STATUS", 1),
        )


    
