import cv2
import time
import threading
import logging
from typing import Optional
from flask import Flask, Response, render_template

import config
import models.consts as consts
from models.message import TOPIC2MSG, get_message_class
from tools.rm_logger import RMColorLogger
from service.core_service import CoreService
from tools.rm_command import Cli, Layer, Option

FPS = 30

logger = RMColorLogger("MainApp")

app = Flask(__name__)
service: Optional[CoreService] = None

@app.route('/video_feed')
def video_feed():
    def generate():
        try:
            while True:
                if service is None:
                    logger.error("CoreService 尚未启动，无法获取视频帧")
                    break
                frame = service.get_cur_handler().get_frame()
                if frame is not None:
                    ret, buffer = cv2.imencode('.jpg', frame)
                    if ret:
                        yield (b'--frame\r\n'
                               b'Content-Type: image/jpeg\r\n\r\n' + 
                               buffer.tobytes() + b'\r\n')
                time.sleep(1 / FPS)
        except Exception as e:
            logger.error(f"视频流生成器发生错误: {e}")
        # # 每次调用 generate 都创建新的 handler
        # handler = NormalImgSource(host="127.0.0.1", port=12346)
        # handler.start()
        
        # try:
        #     while True:
        #         frame = handler.get_frame()
        #         if frame is not None:
        #             ret, buffer = cv2.imencode('.jpg', frame)
        #             if ret:
        #                 yield (b'--frame\r\n'
        #                        b'Content-Type: image/jpeg\r\n\r\n' + 
        #                        buffer.tobytes() + b'\r\n')
        #         time.sleep(1 / FPS)
        #         logger.debug("成功获取并编码一帧视频数据，正在发送...")
        # finally:
        #     # 确保连接关闭时清理资源
        #     handler.stop()
        #     logger.info("视频流生成器已停止，UDP接收线程已关闭")
    
    return Response(generate(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    return render_template('index.html')


def run_flask():
    # Flask 关闭 reloader/debug，避免开发重载导致 service 重复初始化。
    app.run(host='127.0.0.1', port=5000, use_reloader=False, debug=False)
    

def start_flask(blocking=True):
    if blocking:
        run_flask()
    else:
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()


def configure_logging_modes(start_log: bool):
    """按启动模式切换日志策略。"""
    config.Config.RECORD_LOG = False
    config.Config.IF_LOG = start_log

    if start_log:
        app.logger.disabled = False
        logging.getLogger("werkzeug").disabled = False
    else:
        # app.run 的启动横幅不是走常规 logger，这里单独静默。
        try:
            import flask.cli
            flask.cli.show_server_banner = lambda *args, **kwargs: None
        except Exception:
            pass

        app.logger.disabled = True
        werkzeug_logger = logging.getLogger("werkzeug")
        werkzeug_logger.disabled = True
        werkzeug_logger.setLevel(logging.CRITICAL)

    RMColorLogger.reload_all_loggers()

def start_log_or_console(service, start_log=True):
    # 这里可以根据需要选择启动日志界面或者命令行界面

    configure_logging_modes(start_log)

    if start_log:
        print("正在启动日志界面...")
    else:
        print("正在启动命令行服务（需要连接上MQTT broker才可进入界面，Ctrl+C退出）...")

    
    started = service.run(blocking=False)
    if not started:
        print("启动已取消，程序退出。")
        return

    if start_log:
        start_flask(blocking=True)
    else:
        start_flask(blocking=False)
        start_cli(service)

def set_mqtt_source():
    if service is None:
        logger.error("CoreService 尚未启动，无法切换到 MQTT 图传源")
        return
    service.use_mqtt_source_for_test()

def set_udp_source():
    if service is None:
        logger.error("CoreService 尚未启动，无法切换到 UDP 图传源")
        return
    service.use_udp_source_for_test()

def disable_test():
    if service is None:
        logger.error("CoreService 尚未启动，无法修改测试模式")
        return
    service.disable_test_mode()


def show_buffered_logs():
    logs = RMColorLogger.get_global_recent_logs(30)
    if not logs:
        print("暂无日志（最近30条为空）")
        return
    for line in logs:
        print(line)


def set_global_log_level(level: str):
    RMColorLogger.set_global_level(level)
    logger.info(f"日志级别已设置为 {level.upper()}")


def _print_topic_hints(cur_topics: list[str]):
    if not cur_topics:
        print("当前状态机尚无主题数据。")
        return
    print("当前可查询主题:")
    for i, topic in enumerate(cur_topics, start=1):
        print(f"{i}. {topic}")


def _select_index_or_name(options: list[str], prompt: str, target_name: str) -> Optional[str]:
    """支持通过序号或名称进行选择。"""
    raw = input(prompt).strip()
    if not raw:
        print(f"{target_name}不能为空")
        return None

    if raw.isdigit():
        idx = int(raw)
        if 1 <= idx <= len(options):
            return options[idx - 1]
        print(f"{target_name}序号超出范围，请输入 1~{len(options)}")
        return None

    if raw in options:
        return raw

    print(f"未找到{target_name}: {raw}")
    return None


def query_topic_interactive(service: CoreService):
    """交互式查询某个主题的完整状态。"""
    cur_topics = sorted(service.get_all().keys())
    _print_topic_hints(cur_topics)
    topic = _select_index_or_name(cur_topics, "请输入主题编号或名称: ", "主题")
    if topic is None:
        return

    data = service.get(topic)
    if not data:
        print(f"未找到主题: {topic}")
        return

    print(f"主题 {topic} 的当前状态:")
    print(data)


def query_topic_key_interactive(service: CoreService):
    """交互式查询某个主题的某个属性值。"""
    cur_topics = sorted(service.get_all().keys())
    _print_topic_hints(cur_topics)
    topic = _select_index_or_name(cur_topics, "请输入主题编号或名称: ", "主题")
    if topic is None:
        return

    field_names: list[str] = []
    if topic in TOPIC2MSG:
        msg_cls = get_message_class(topic)
        field_names = msg_cls._field_names()

    if field_names:
        print("该主题可访问属性:")
        for i, field_name in enumerate(field_names, start=1):
            print(f"{i}. {field_name}")
        key = _select_index_or_name(field_names, "请输入属性编号或名称: ", "属性")
        if key is None:
            return
    else:
        print("未找到该主题的属性定义，将按输入字段直接查询。")
        key = input("请输入属性名: ").strip()
        if not key:
            print("属性名不能为空")
            return

    if field_names and key not in field_names:
        print(f"属性 {key} 不在该主题定义中")
        return

    value = service.get(topic, key)
    print(f"{topic}.{key} = {value}")

def start_cli(service: CoreService):
    
    """
        - 设计命令类（q=返回）
        - 1. 查询服务状态
        - 1. 查询服务是否在运行（服务包含：flask服务；mqtt服务；udp接收服务；mqtt图传解码线程服务；图传源动态切换服务）
        - 2. 查询当前图传数据源（MQTT/UDP）
        - 3. 状态机（3种：所有状态（dict），某个主题的状态，某个主题的属性的值）
        - 2. 日志
        - 1. 命令行模式（默认）+ 获取日志buffer的内容
        - 2. 实时模式，按q返回命令行模式
        - 3. 日志级别设置（默认INFO，可简写）
        - 3. 测试
        - 1. 启动测试
            - 1. 启用mqtt图传源测试（修改test_config即可）
            - 2. 启用udp图传源测试
        - 2. 禁用测试
        - 4. 其他功能
        - 1. 动态修改客户端的id（需要重启MQTT连接才能生效）
    """
    root_layer = Layer("查询服务状态|日志|测试", "输入对应数字进入子菜单，输入?查看帮助信息，输入q返回上层菜单",
                        Layer("查询服务状态|查询当前图传数据源|状态机查询", "查询核心服务的基本运行状态，查询当前使用的图传数据源（MQTT/UDP），状态机查询，支持查询所有状态、某个主题的状态、某个主题的属性值",
                             Option("查询服务是否在运行", "查询核心服务的基本运行状态", service.print_if_alive),
                             Option("查询当前图传数据源", "查询当前使用的图传数据源（MQTT/UDP）", service.print_current_source),
                             Layer("查询所有|查询某个主题|查询某个主题的属性值", "状态机查询，支持查询所有状态、某个主题的状态、某个主题的属性值",
                                  Option("查询所有状态", "获取所有状态数据，便于调试使用", service.print_all_topics),
                                    Option("查询某个主题的状态", "输入主题名称，获取该主题的状态数据", query_topic_interactive, service),
                                    Option("查询某个主题的属性值", "输入主题名称和属性名称，获取该属性的值", query_topic_key_interactive, service)
                                  )
                             ),
                        Layer("获取日志|日志级别设置", "日志功能，支持命令行模式和实时模式，并且可以设置日志级别",
                            Option("获取日志", "获取日志buffer的内容", show_buffered_logs),
                            # Option("实时模式", "实时输出日志，按q返回命令行模式"),
                            Layer("DEBUG|INFO|WARNING|ERROR|CRITICAL", "设置日志级别，例如 DEBUG、INFO、WARNING、ERROR、CRITICAL",
                                    Option("DEBUG", "设置日志级别为 DEBUG", set_global_log_level, "DEBUG"),
                                    Option("INFO", "设置日志级别为 INFO", set_global_log_level, "INFO"),
                                    Option("WARNING", "设置日志级别为 WARNING", set_global_log_level, "WARNING"),
                                    Option("ERROR", "设置日志级别为 ERROR", set_global_log_level, "ERROR"),
                                    Option("CRITICAL", "设置日志级别为 CRITICAL", set_global_log_level, "CRITICAL")
                                  )
                             ),
                        Layer("启用测试|禁用测试", "测试功能，支持启用MQTT图传源测试和UDP图传源测试",
                              Layer("启动mqtt测试|启动udp测试", "启用mqtt图传源测试|启用udp图传源测试", 
                                    Option("启用mqtt图传源测试", "启用mqtt图传源测试（修改test_config即可）", set_mqtt_source),
                                    Option("启用udp图传源测试", "启用udp图传源测试（修改test_config即可）", set_udp_source),
                                    ),
                              Option("禁用测试", "禁用mqtt与udp图传测试", disable_test) 
                              ),
                        # Layer("其他功能", "目前包含：修改客户端ID", 
                        #       Option("动态修改客户端ID", "输入新的客户端ID，修改后需要重启MQTT连接", )
                        #       )
                       )
    cli = Cli(root_layer)
    cli.start_loop()

if __name__ == '__main__':
    # [部署约束]
    # 官方协议下 MQTT 服务端固定为 192.168.12.1:3333，
    # 而 UDP 图传接收必须绑定本机地址（建议 0.0.0.0 监听所有网卡）。
    # 两者语义不同，禁止复用为同一个 host 参数。
    
    service = CoreService(
        side=consts.Sides.RED,
        robot=consts.RobotTypes.INFANTRY,
        infantry_select=2,
        mqtt_host="127.0.0.1",
        port_mqtt=3333,
        udp_bind_host="0.0.0.0",
        port_udp=3334,
        # test_config=consts.TestConfig(if_test=True, if_mqtt_source=True)
    )
    start_log_or_console(service, start_log=False)