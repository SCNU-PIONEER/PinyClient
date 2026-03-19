# reflex_cil 包架构说明

本文档拆解 `reflex_cil` 包的实现结构，细化到模块、类、函数与关键全局变量，并说明每一项在整体链路中的含义。

## 1. 包定位

`reflex_cil` 是 Reflex 前端应用的 Python 侧核心包，职责是：

- 承载 UI 状态与页面布局。
- 对接 MQTT 协议（下行状态订阅 + 上行控制发送）。
- 在应用启动时拉起图传服务（UDP 收流、FFmpeg 转码、WebSocket 广播）。

## 2. 目录结构

### 2.1 `reflex_cil/__init__.py`

- 含义：包初始化文件。
- 当前状态：空文件，仅用于声明 `reflex_cil` 为可导入 Python 包。

### 2.2 `reflex_cil/reflex_cil.py`

- 含义：Reflex 页面主模块，定义状态机 `DashboardState`、组件构造函数和页面入口 `index`。
- 额外行为：模块导入时会调用 `video_server.start()`，自动启动图传服务线程组。

### 2.3 `reflex_cil/protocol_bridge.py`

- 含义：协议桥模块，封装 MQTT 客户端与 protobuf 消息解析/发送。
- 产出对象：全局单例 `bridge = ProtocolBridge()`，供页面状态层直接调用。

### 2.4 `reflex_cil/video_server.py`

- 含义：图传服务模块，完成 UDP 分片重组、FFmpeg 转码和 WebSocket 广播。
- 设计特征：混合线程 + asyncio 架构，兼顾高吞吐与页面端实时播放。

## 3. `reflex_cil.py` 细化

### 3.1 模块级导入与初始化

#### 3.1.1 `_video_server.start()`

- 含义：在模块加载阶段启动图传服务。
- 作用：避免页面首次进入时再启动造成延迟，保证视频链路尽早就绪。

#### 3.1.2 常量映射导入

- `SHOOTER_OPTION_TO_ENUM`：将 UI 文本映射为协议枚举值（发射机构性能体系）。
- `CHASSIS_OPTION_TO_ENUM`：将 UI 文本映射为协议枚举值（底盘性能体系）。
- `DART_TARGET_TO_ID`：将飞镖目标文本映射为协议目标 ID。
- `bridge`：协议桥单例，负责收发 MQTT/protobuf。

### 3.2 类 `DashboardState(rx.State)`

- 含义：Reflex 全局状态容器。
- 作用：保存页面展示数据、响应用户事件、驱动协议交互、执行后台同步。

#### 3.2.1 状态字段（按业务分组）

##### 3.2.1.1 控制项

- `launcher_option`：当前发射机构策略。
- `dart_target`：当前飞镖目标。
- `chassis_option`：当前底盘策略。
- `deploy_enabled`：部署模式开关。

##### 3.2.1.2 比赛与战况数据

- `total_time` / `remaining_time`：总时长与剩余时间。
- `economy_now` / `economy_total`：当前经济与累计经济。
- `tech_level`：建筑科技等级。
- `our_damage` / `enemy_damage`：双方累计伤害。
- `our_base_hp` / `our_outpost_hp`：己方基地与前哨状态（百分比）。
- `enemy_base_hp` / `enemy_outpost_hp`：敌方基地与前哨状态（百分比）。

##### 3.2.1.3 能力与资源状态

- `can_respawn` / `can_pay_for_respawn`：免费复活、付费复活是否可用。
- `can_remote_ammo` / `can_remote_heal`：远程补弹、远程补血是否可用。
- `gold_respawn_cost`：金币复活消耗。
- `dart_open_status`：飞镖闸门状态（关/开闸中/已开）。
- `robot_level`：机器人等级。
- `current_exp` / `upgrade_exp`：当前经验与升级所需经验。

##### 3.2.1.4 弹药输入显示

- `ammo_17_display`：17mm 输入框值（字符串形式，便于 UI 直接绑定）。
- `ammo_42_display`：42mm 输入框值。

##### 3.2.1.5 服务端同步对照与告警

- `server_launcher_option` / `server_chassis_option` / `server_dart_target` / `server_deploy_enabled`：服务端回传值快照。
- `warning_message`：本地值与服务端值不一致时的提示语。
- `_server_*_seen`：标记某字段是否已收到过服务端值，避免初始空值误报。

##### 3.2.1.6 连接与循环控制

- `protocol_connected`：协议桥连接状态。
- `protocol_status`：可显示给用户的连接描述。
- `_sync_loop_started`：后台同步循环防重入标记。

#### 3.2.2 事件函数（`@rx.event`）

##### 3.2.2.1 `init_data(self)`

- 含义：页面加载时初始化协议连接状态。
- 行为：调用 `bridge.connect()`，并写入 `protocol_status` 与 `protocol_connected`。

##### 3.2.2.2 `_update_sync_warning(self)`

- 含义：内部辅助函数，计算“本地修改可能未同步”的告警信息。
- 行为：对比本地控制值与服务端回传值，拼接差异字段名称。

##### 3.2.2.3 `sync_loop(self)`（后台事件）

- 含义：周期性拉取协议桥快照并刷新页面状态。
- 行为：
  - 防止重复启动。
  - 轮询 `bridge.poll()`。
  - 增量更新各状态字段。
  - 更新同步告警与连接状态。
  - 异常时退出循环并清理 `_sync_loop_started`。

##### 3.2.2.4 控制项变更

- `set_launcher_option(self, value)`：设置发射机构策略并发送 `RobotPerformanceSelectionCommand`。
- `set_dart_target(self, value)`：设置飞镖目标并发送 `DartCommand`（仅改目标，不触发发射）。
- `set_chassis_option(self, value)`：设置底盘策略并发送 `RobotPerformanceSelectionCommand`。
- `enable_deploy(self)`：开启部署模式并发送 `HeroDeployModeEventCommand(mode=1)`。
- `disable_deploy(self)`：退出部署模式并发送 `HeroDeployModeEventCommand(mode=0)`。

##### 3.2.2.5 弹药输入与发送

- `set_17mm_amount(self, value)`：过滤非数字字符，更新 17mm 输入框值。
- `set_42mm_amount(self, value)`：过滤非数字字符，更新 42mm 输入框值。
- `send_17mm(self)`：读取 17mm 数值并按 10 的倍数对齐后发送 `CommonCommand(cmd_type=1)`。
- `send_42mm(self)`：发送 `CommonCommand(cmd_type=2)`。

##### 3.2.2.6 战术动作发送

- `send_respawn(self)`：发送免费复活 `CommonCommand(cmd_type=3)`。
- `send_gold_respawn(self)`：发送金币复活 `CommonCommand(cmd_type=4)`。
- `send_remote_ammo(self)`：发送远程补弹 `CommonCommand(cmd_type=5)`。
- `send_remote_heal(self)`：发送远程补血 `CommonCommand(cmd_type=6)`。
- `open_dart_gate(self)`：发送飞镖开闸命令（不确认发射）。
- `launch_dart(self)`：发送飞镖开闸+发射确认命令。
- `activate_rune(self)`：发送能量机关激活命令。

#### 3.2.3 计算属性（`@rx.var`）

- `dart_indicator_class(self)`：将 `dart_open_status` 映射为前端样式类。
- `our_base_hp_width(self)`：返回己方基地血条宽度字符串。
- `our_outpost_hp_width(self)`：返回己方前哨血条宽度字符串。
- `enemy_base_hp_width(self)`：返回敌方基地血条宽度字符串。
- `enemy_outpost_hp_width(self)`：返回敌方前哨血条宽度字符串。

### 3.3 组件构造函数

#### 3.3.1 `action_button(label, on_click=None, disabled=False)`

- 含义：统一按钮样式封装。

#### 3.3.2 `ammo_action_cell(title, value, on_change, on_click)`

- 含义：弹药输入+发送按钮组合组件。

#### 3.3.3 `select_cell(placeholder, options, value, on_change)`

- 含义：统一下拉框组件，支持空值时的占位样式。

#### 3.3.4 `status_bar_item(label, value, width)`

- 含义：基地/前哨状态条组件。

### 3.4 页面入口

#### 3.4.1 `index()`

- 含义：页面主布局函数。
- 内容：
  - 顶部视频区和地图区占位。
  - 左侧控制区（弹药、复活、远程支援、部署、飞镖、策略下拉）。
  - 右侧信息区（时间、经济、科技、伤害、血量条）。
  - 协议连接状态与同步告警展示。

#### 3.4.2 `app = rx.App()` 与 `app.add_page(...)`

- 含义：应用实例与页面注册。
- `on_load`：绑定 `DashboardState.init_data` 与 `DashboardState.sync_loop`，实现“进入页面即连接+同步”。

## 4. `protocol_bridge.py` 细化

### 4.1 常量与映射

- `SHOOTER_OPTION_TO_ENUM`：发射体系 UI 文本 -> 枚举值。
- `CHASSIS_OPTION_TO_ENUM`：底盘体系 UI 文本 -> 枚举值。
- `DART_TARGET_TO_ID`：飞镖目标文本 -> 目标 ID。
- `DART_ID_TO_TARGET`：目标 ID -> 文本（用于下行回显）。
- `SHOOTER_ENUM_TO_OPTION`：发射枚举 -> 文本。
- `CHASSIS_ENUM_TO_OPTION`：底盘枚举 -> 文本。

### 4.2 类 `ProtocolBridge`

- 含义：MQTT 协议桥，负责“订阅解析下行 + 统一发送上行 + 提供快照轮询接口”。

#### 4.2.1 `__init__(self, host, port, client_id)`

- 含义：构造 MQTT 客户端并绑定连接、断开、消息回调。
- 关键状态：
  - `_connected`：连接标记。
  - `_cache` / `_latest_snapshot`：消息缓存与最近快照。
  - `_base_health_max` 等：血量归一化参考上限。

#### 4.2.2 `is_connected(self)`（property）

- 含义：对外暴露连接状态。

#### 4.2.3 `connect(self)`

- 含义：发起 MQTT 连接并启动网络循环线程。
- 返回值：用于 UI 展示的状态字符串（成功尝试/失败原因）。

#### 4.2.4 MQTT 回调函数

- `_on_connect(...)`：连接成功后订阅全部下行 topic。
- `_on_disconnect(...)`：更新连接状态为断开。
- `_on_message(...)`：按 topic 解析 protobuf，生成统一字段更新字典并写入快照。

#### 4.2.5 解析辅助函数

- `_normalize_percent(value, max_value)`：将血量转换为 0-100 百分比。
- `_topic_name(topic)`：提取 topic 末段名称用于分发。

#### 4.2.6 轮询与发送函数

- `poll(self)`：返回当前最新快照副本（供 UI 循环拉取）。
- `_publish(self, topic, pb_message)`：统一 protobuf 序列化与 MQTT 发送入口。
- `send_common_command(self, cmd_type, param)`：发送 `CommonCommand`。
- `send_robot_performance_selection(self, shooter, chassis, sentry_control)`：发送性能体系指令。
- `send_hero_deploy_mode(self, enabled)`：发送部署模式事件。
- `send_rune_activate(self)`：发送能量机关激活指令。
- `send_dart_command(self, target_id, open_gate, launch_confirm)`：发送飞镖控制指令。

### 4.3 全局对象

- `bridge = ProtocolBridge()`
- 含义：模块级单例，供 `DashboardState` 直接调用，避免多连接实例冲突。

## 5. `video_server.py` 细化

### 5.1 模块用途

- 含义：把机器人侧 UDP HEVC 分片视频流转为浏览器可播放的 WebSocket 分片 MP4（H.264）流。

### 5.2 配置常量

- `UDP_PORT` / `WS_PORT` / `UDP_BIND`：监听地址。
- `MAX_FRAME_BYTES` / `MAX_BUFFERED_FRAMES`：帧重组内存上限控制。
- `FRAME_TIMEOUT_S` / `CLEANUP_INTERVAL_S`：重组超时与清理周期。
- `FFMPEG_INPUT_QUEUE_MAX`：送入 FFmpeg 的输入队列容量。
- `FFMPEG_STALL_TIMEOUT_S` / `FFMPEG_WATCHDOG_INTERVAL_S`：转码卡死检测参数。
- `FFMPEG_INPUT_RESUME_RESTART_GAP_S`：长时间断流恢复时的主动重启阈值。

### 5.3 共享运行状态（全局变量）

- `_loop` / `_async_queue`：WebSocket 广播的 asyncio 上下文。
- `_ws_clients` / `_ws_lock`：客户端集合及其互斥锁。
- `_init_segment` / `_init_segment_pending` / `_init_segment_ready`：初始化片段缓存，用于新客户端秒开。
- `_ffmpeg_proc` / `_ffmpeg_lock`：FFmpeg 进程对象及同步锁。
- `_ffmpeg_input_queue`：HEVC 帧输入缓冲队列。
- `_last_ffmpeg_input_at` / `_last_ffmpeg_output_at` / `_last_hevc_frame_at`：时序监控时间戳。
- `_frame_buf`：UDP 分片重组缓存表。
- `_started` / `_start_lock`：服务启动幂等控制。

### 5.4 关键函数分层

#### 5.4.1 广播与初始化片段处理

- `_broadcast_chunk(chunk)`：线程安全投递转码输出到异步广播队列。
- `_reset_init_segment()`：重置初始化片段状态（通常在 FFmpeg 重启后调用）。
- `_capture_init_segment(chunk)`：从 MP4 片段流中提取 `ftyp/moov` 等初始化数据。

#### 5.4.2 FFmpeg 生命周期与喂流

- `_start_ffmpeg()`：查找并启动 FFmpeg 子进程。
- `_ffmpeg_reader(proc)`：读取 FFmpeg stdout 并广播给 WS 客户端。
- `_stop_ffmpeg_process(proc)`：优雅停止/强制结束 FFmpeg 进程。
- `_ensure_ffmpeg_running_locked()`：加锁条件下确保 FFmpeg 正在运行。
- `_restart_ffmpeg(reason)`：按原因重启 FFmpeg 并重置相关状态。
- `_enqueue_hevc_frame(frame)`：将重组后的 HEVC 帧压入输入队列。
- `_ffmpeg_writer_thread()`：后台线程持续从输入队列取帧并写入 FFmpeg stdin。
- `_ffmpeg_watchdog_thread()`：监控转码输出与进程状态，发现卡死自动重启。
- `_write_hevc_frame(frame)`：写入入口，支持断流恢复场景主动重启转码器。

#### 5.4.3 UDP 收包与帧重组

- `_cleanup_frames()`：清除超时未完成帧，避免缓存泄漏。
- `_ingest_packet(data)`：解析单个 UDP 包头，按 `frame_id/slice_id` 重组完整帧。
- `_udp_thread()`：持续接收 UDP 并驱动重组流程。

#### 5.4.4 WebSocket 服务

- `_broadcaster()`：从异步队列取 chunk，广播给所有在线 WS 客户端。
- `_ws_handler(websocket, *_args)`：处理客户端连接生命周期，并在连接时补发初始化片段。
- `_serve()`：创建 WS 服务并常驻运行。
- `_ws_server_thread()`：在线程中运行 asyncio 事件循环。

#### 5.4.5 对外 API

- `start()`：唯一公开入口，幂等启动 FFmpeg writer/watchdog、UDP 接收线程和 WS 线程。

## 6. 模块协作关系

### 6.1 启动阶段

1. 导入 `reflex_cil.py` 时调用 `video_server.start()`。
2. 打开页面触发 `on_load`：`DashboardState.init_data` 连接协议桥。
3. `DashboardState.sync_loop` 开始轮询 `bridge.poll()` 并刷新页面。

### 6.2 下行状态流

1. 协议服务通过 MQTT 发布 protobuf 消息。
2. `ProtocolBridge._on_message` 解析并写入 `_latest_snapshot`。
3. `DashboardState.sync_loop` 拉取快照并更新 UI 状态字段。

### 6.3 上行控制流

1. 用户点击页面控件触发 `DashboardState` 事件。
2. 事件函数调用 `bridge.send_*` 组装 protobuf。
3. `ProtocolBridge._publish` 发送到对应 MQTT topic。

### 6.4 图传流

1. UDP 分片视频包进入 `_udp_thread`。
2. `_ingest_packet` 完成帧重组后调用 `_write_hevc_frame`。
3. FFmpeg 转码输出由 `_ffmpeg_reader` 捕获并送入 `_broadcast_chunk`。
4. `_broadcaster` 广播到浏览器 WebSocket，页面 JS 用 MSE 追加播放。

## 7. 可维护性建议（针对当前结构）

- 若要扩展新协议字段，优先在 `ProtocolBridge._on_message` 统一命名后再给 `DashboardState` 消费，避免 UI 层直接耦合 protobuf 细节。
- 若要增加新控制命令，建议复用 `bridge.send_*` 统一出口，保持页面层只关心业务语义。
- 图传若出现长时间无画面，优先检查 FFmpeg 可用性、UDP 输入速率和 watchdog 重启日志。