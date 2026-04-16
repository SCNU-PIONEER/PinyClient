# service 目录说明

本目录是运行时服务层，负责：
1. MQTT 收发与状态缓存。
2. UDP/MQTT 两种图传源接入与切换。
3. 核心生命周期管理（启动、停止、运行模式切换）。

## 目录结构

- `core_service.py`: 服务主入口，整合 MQTT 与图传源。
- `mqtt_client.py`: MQTT 客户端封装和 topic 状态管理器。
- `img_receiver.py`: 图传接收实现（UDP 源 + MQTT 源）。
- `states_manager.py`: 历史状态访问草稿（当前主要逻辑已迁移到 `mqtt_client.py` 的 `MQTTStateManager`）。
- `test_udp_sender.py`: 本地 UDP 图传模拟发送器。

## 核心逻辑

### 1) core_service.py

`CoreService` 是当前运行时编排器：

- 初始化 `RMMQTTClient`（订阅下行 topic，回调 `update_state`）。
- 初始化图传源：
  - `NormalImgSource`（UDP 3334）。
  - `MqttImgSource`（读取 `CustomByteBlock` 状态）。
- 启动后由 `_mode_monitor_loop()` 根据 `DeployModeStatusSync.status` 动态切换图传源：
  - `status == 1` -> MQTT 图传源。
  - 否则 -> UDP 图传源。

生命周期接口：

- `start()`: 启动 MQTT + 模式监控线程。
- `run(blocking=True)`: 可阻塞运行，也可非阻塞后台运行。
- `stop()`: 停止模式监控、MQTT 客户端和两类图传线程。

### 2) mqtt_client.py

`RMMQTTClient` 采用 paho `loop_start()` 的单网络线程模型。

关键流程：

1. `connect()` 建立连接。
2. `_on_connect()` 自动订阅 `subscribe_topics`。
3. `_on_message()` 通过 `handler[topic]` 取消息类并反序列化。
4. 回调给上层 `callback(parsed_msg)`。
5. `update(data)` 将解析结果写入 `MQTTStateManager`。

`MQTTStateManager` 特点：

- 线程安全（`RLock`）。
- 支持按 topic 存储状态快照。
- `update()` 支持默认值补全与空消息重置。

### 3) img_receiver.py

#### NormalImgSource（UDP）

- 按协议头 `>HHI` 解析分片：`frame_id/chunk_id/total_length`。
- 分片缓存、超时重置、完整帧拼接。
- 可选 `cv_debug` 直接显示画面。

#### MqttImgSource（MQTT）

- 通过 `state_manager.get("CustomByteBlock")` 轮询最新包。
- 作为吊射模式图传源入口（目前仍有 TODO，主要用于模式切换流程打通）。

## 数据流

### 下行数据

1. MQTT 收到 protobuf 二进制。
2. `mqtt_client.py` 解析为 `BaseMessage` 子类对象。
3. `core_service.update_state()` 调用 `core_mqtt.update(data)`。
4. 状态进入 `MQTTStateManager`，供模式切换和业务读取。

### 上行数据

1. `core_service.publish(topic, dict)`。
2. 用模型类 `from_dict()` 构造消息。
3. `to_protobuf()` 后发布 MQTT。

## 联调方式

1. 启动核心服务：

```bash
python -i core_service.py
```

2. 非阻塞模式下可在 REPL 操作：

- `service.publish(...)` 发送测试消息。
- `service.stop()` 停止所有后台线程。

3. 本地 UDP 图传联调：

```bash
python test_udp_sender.py
```
4. 待完善功能：MQTT接收端逻辑