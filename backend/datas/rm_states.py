"""
RoboMaster 状态机模块
与 MQTT 逻辑解耦，可独立使用，供后端 HTTP 接口或前端直接读取。
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from static.rm_consts import *  # pyright: ignore[reportImplicitRelativeImport]
from static.rm_dataclasses import *  # pyright: ignore[reportImplicitRelativeImport]


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


    
