import socket
import struct
import cv2
import sys
import numpy as np
import threading
import time
from typing import Optional
from dataclasses import dataclass

sys.path.append("..")  # 添加项目根目录到sys.path，方便导入模块

from models.message import CustomByteBlock
from .mqtt_client import RMMQTTClient
from tools.rm_logger import RMColorLogger
    
logger = RMColorLogger("UDPReceiver")

FRAME_PACK_FORMAT = '>HHI'  # 帧编号（2 byte）当前帧内分片序号（2 byte）当前帧总字节数（4 byte）
MAX_DGRAM = 300  # 最大UDP数据包大小（字节），这里设置为300字节，实际可用数据为292字节（300 - 8字节UDP头部）

class NormalUDPPackage:
    def __init__(self, data: bytes):
        self.data = data
    
    def parse(self) -> tuple[int, int, int, bytes]:
        """解析UDP数据包并返回状态"""
        # 帧编号（2 byte）当前帧内分片序号（2 byte）当前帧总字节数（4 byte）
        frame_id, chunk_id, total_length = struct.unpack(FRAME_PACK_FORMAT, self.data[:8])
        return (frame_id, chunk_id, total_length, self.data[8:])

class MqttUdpPackage(CustomByteBlock):
    # def __init__(self, data: bytes):
    #     # 这里直接保存原始UDP字节，避免BaseMessage/dataclass字段代理导致读取到默认值b''。
    #     self.raw_data = data

    def parse(self):
        """解析UDP数据包并返回状态"""
        data = self.from_protobuf(self.data)  # 从Protobuf消息中提取原始UDP字节
        return data
    
class ImgSource:
    def __init__(self):
        # 帧缓冲区
        self.frame_buffer: dict[int, bytes] = {}
        self.frame_id: int = -1  # 当前帧编号
        self.total_length: int = 0  # 当前帧总字节数
        self.cur_length: int = 0  # 当前帧已接收字节数
        self.last_activity: float = time.time()  # 上次接收数据的时间

        # 线程控制
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # 存储最新完整帧
        self.latest_frame: Optional[np.ndarray] = None  # 存储最新帧数据
        self.frame_lock = threading.Lock()  # 保护latest_frame的锁

        # 超时清理（防止死等丢包）
        self.timeout_threshold = 10.0  # 超时时间（秒）

        # 每帧大小
        self.width = 100
        self.height = 75
        self.channels = 3
        self.expected_frame_size = self.width * self.height * self.channels  # 100x75的RGB帧大小

        # 使用cv调试显示
        self.cv_debug = False
    
    def _init_frame(self, frame_id: int, total_length: int):
        """初始化当前帧的接收状态"""
        self.frame_id = frame_id
        self.frame_buffer.clear()
        self.total_length = total_length
        self.cur_length = 0
        self.last_activity = time.time()

    def _update_frame(self, chunk_id: int, chunk_data: bytes):
        """更新当前帧的接收状态"""
        # 存储分片数据
        if chunk_id not in self.frame_buffer:
            self.frame_buffer[chunk_id] = chunk_data
            self.cur_length += len(chunk_data)
            self.last_activity = time.time()

    def _check_timeout(self):
        """检查当前帧是否超时，如果超时则重置状态"""
        if time.time() - self.last_activity > self.timeout_threshold and self.frame_id != -1:
            logger.warning(f"帧 {self.frame_id} 接收超时，重置状态，已接收 {self.cur_length}/{self.total_length} 字节")
            self._init_frame(-1, 0)

    def _try_assemble_frame(self):
        """尝试拼接当前帧，如果已接收完整则返回完整帧数据，否则返回None"""
        if self.cur_length == self.total_length and self.total_length > 0:
            # 按照分片顺序拼接成完整帧数据
            frame_data = b''.join(self.frame_buffer[i] for i in sorted(self.frame_buffer.keys()))
            try:
                frame = np.frombuffer(frame_data, dtype=np.uint8).reshape((self.height, self.width, self.channels))
                # 存储最新帧
                # 为什么要用锁？因为main线程在接收数据时会更新latest_frame，而另一个线程可能在读取latest_frame进行显示或其他处理，使用锁可以避免数据竞争和不一致问题
                # with self.frame_lock:  # 获取锁，确保在更新latest_frame时不会被其他线程同时访问
                # frame.copy()是为了确保在更新latest_frame时不会被其他线程同时访问导致数据不一致问题
                with self.frame_lock:
                    self.latest_frame = frame.copy()  # 更新最新帧
                # 成功后立即重置，避免在下一帧到来时重复拼接同一帧。
                self._init_frame(-1, 0)
                return frame
            except Exception as e:
                logger.error(f"处理帧 {self.frame_id} 时发生错误: {e}")
            # 重置状态，准备处理下一帧
            self.frame_id = -1
            return None
        return None

    def start(self):
        """启动接收线程"""
        if self.running:
            logger.warning("UDP服务器已经在运行")
            return
        self.running = True
        self.thread = threading.Thread(target=self._receive_loop, daemon=True)
        self.thread.start()
        logger.info("UDP服务器线程已启动")
    
    def stop(self):
        """停止接收线程"""
        if not self.running:
            logger.warning("UDP服务器已经停止")
            return
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=5.0)  
        logger.info("UDP服务器线程已停止")


    def get_frame(self) -> Optional[np.ndarray]:
        """获取最新完整帧数据"""
        with self.frame_lock:
            if self.latest_frame is not None:
                logger.debug("成功获取最新帧数据")
                return self.latest_frame
        return None

    def _receive_loop(self):
        """接收循环，子类实现具体的接收逻辑"""
        raise NotImplementedError("子类必须实现 _recv_loop 方法")

class MqttImgSource(ImgSource):
    def __init__(self, mqtt: RMMQTTClient, host: str = "127.0.0.1", port: int = 3333) -> None:
        super().__init__()
        self.mqtt_client = mqtt
        self.thread = None  # MQTT接收线程
        self.last_updated = time.time()  # 上次更新帧的时间

    # def _mqtt_message_handler(self, payload: bytes):
    #     """"""
    #     logger.debug(f"收到MQTT消息，长度: {len(payload)} 字节")
    #     try:
    #         pkg = MqttUdpPackage(data=payload)
    #         logger.debug(f"protobuf消息解析成功，原始UDP数据长度: {len(pkg.data)} 字节")
    #         logger.debug(f"内容：{pkg.data}")  
    #     except Exception as e:
    #         logger.error(f"处理MQTT消息时发生错误: {e}")

    # def _receive_loop(self):
    #     """MQTT接收循环"""
    #     logger.info("MQTT客户端正在连接并订阅主题...")
    #     try:
    #         # 如果 start_listening 会阻塞，这里会一直运行
    #         self.mqtt_client.start_listening()
    #     except Exception as e:
    #         logger.error(f"MQTT接收循环出错: {e}")
    #     finally:
    #         logger.info("MQTT接收循环结束")
    def _process_custom_byte_block(self):
        """处理CustomByteBlock消息，提取其中的UDP数据并更新帧状态"""
        while self.running:
            try:
                data = self.mqtt_client.state_manager.get("CustomByteBlock")
                latest = data["_last_update"]
                if (latest - self.last_updated) > 0:
                    # 说明新的包来了，应该更新了，TODO: 但现在还不知道包的结构，所以先time.sleep(1)，防止消息爆炸
                    logger.debug(f"检测到新的CustomByteBlock消息，更新时间戳: {latest}")
                    time.sleep(1)  # 等待消息完全更新
                else:
                    time.sleep(0.1)  # 没有新包，稍等一下
                    continue
            except Exception as e:
                logger.error(f"无法接收CustomByteBlock消息, 错误信息: {e}")
                time.sleep(1)

    def start(self):
        if self.running:
            logger.warning("MQTT UDP服务器已经在运行")
            return
        self.running = True
        self.thread = threading.Thread(target=self._process_custom_byte_block, daemon=True)
        self.thread.start()
        logger.info("MQTT UDP服务器线程已启动")


    def stop(self):
        """停止接收线程"""
        if not self.running:
            logger.warning("MQTT UDP服务器已经停止")
            return
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=5.0)
        logger.info("MQTT UDP服务器线程已停止")

class NormalImgSource(ImgSource):
    def __init__(self, host: str = "127.0.0.1", port: int = 3334) -> None:
        super().__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.sock.bind((host, port))
        except Exception as e:
            logger.error(f"无法绑定UDP端口 {port}，错误信息: {e}")
            # logger.error(f"端口 {port} 不可用")
            # exit(1)
        self.sock.settimeout(1.0)  # 设置接收超时时间，避免阻塞过久
    
    def _receive_loop(self):
        """
         - UDP接收循环
         - 1. 来源于3334端口的udp数据包
         - 2. 来源于MQTT服务的帧数据
        """
        logger.info(f"UDP接收循环已启动，监听{self.sock.getsockname()}，等待数据包...")
        # 外层循环
        while self.running:
            try:
                data, addr = self.sock.recvfrom(MAX_DGRAM)
                # 使用MQTT服务代替数据

                if len(data) < 8:
                    logger.warning(f"此数据包无效，忽略")
                    continue
                frame_id, chunk_id, total_length = NormalUDPPackage(data=data).parse()[:3]
                chunk_data = data[8:]

                self._check_timeout()  # 检查是否超时，为什么要在每次接收数据包时检查超时？因为如果某个帧的分片丢失了，可能会导致一直等待这个帧完成而无法继续接收后续帧，通过在每次接收数据包时检查超时，可以及时重置状态，避免死等丢包的情况
                
                if frame_id != self.frame_id:
                    # 接收到新帧，先尝试拼接上一帧（如果有的话），然后初始化新帧状态
                    if self.frame_id != -1:  # 也就是上一帧存在
                        logger.debug(f"接收到新帧 {frame_id}，当前帧 {self.frame_id} 已完成接收，尝试拼接上一帧")
                        self._try_assemble_frame()  # 尝试拼接上一帧
                    self._init_frame(frame_id, total_length)  # 初始化新帧状态
                self._update_frame(chunk_id, chunk_data)  # 更新当前帧状态
                complete_frame = self._try_assemble_frame()  # 尝试拼接当前帧
                if complete_frame is not None and self.cv_debug:
                    cv2.imshow("UDP Stream", complete_frame)
                    cv2.waitKey(1)  # 必须调用waitKey才能显示窗口
            except socket.timeout:
                logger.debug("UDP接收超时，检查当前帧状态...")
                self._check_timeout()  # 定期检查超时
                continue
            except Exception as e:
                logger.error(f"接收数据包时发生错误: {e}")
        logger.info("UDP服务器已停止")


if __name__ == "__main__":

    # bt = b'\x00\x01\x00\x00\x00\x00\x00\x05hello'  # 模拟一个UDP数据包，帧编号1，分片0，总长度5，数据为"hello"
    # pkg = NormalUDPPackage(bt)
    # print(pkg.parse())
    # pkg.data = bt

    # udp_handler = NormalImgSource(port=3334)
    # udp_handler.cv_debug = True  # 开启cv调试显示
    # udp_handler.start()

    # try:
    #     while True:
    #         time.sleep(1)  # 主线程可以执行其他任务，这里只是简单地保持运行
    # except KeyboardInterrupt:
    #     logger.info("收到退出信号，正在关闭UDP服务器...")
    # finally:
    #     udp_handler.stop()

    # test mqtt
    # mqtt_ = MqttImgSource(host="127.0.0.1", port=3333)
    # mqtt_.start()

    pass
