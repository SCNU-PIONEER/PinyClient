import socket
import cv2
import struct
import time

VIDEO_PATH = "../assets/oceans.mp4"
UDP_IP = "127.0.0.1"
UDP_PORT = 3334
MAX_DGRAM = 292  # 这里是有效载荷

if __name__ == "__main__":
    # 创建UDP套接字
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    FORMAT = '>HHI'  # 帧编号（2 byte）当前帧内分片序号（2 byte）当前帧总字节数（4 byte）
    # 发送数据到UDP服务器
    # server_address = ("127.0.0.1", 12346)
    print(f"开始发送视频数据到 {UDP_IP}:{UDP_PORT}...")
    while True:
        cap = cv2.VideoCapture(VIDEO_PATH)
        counter = 0
        while cap.isOpened():
            # ret：表示是否成功读取到视频帧，frame：表示读取到的视频帧
            ret, frame = cap.read()
            if not ret:
                print("视频读取完成，准备重新发送")
                break
            # 压缩帧大小（可选：调整尺寸和质量）
            frame = cv2.resize(frame, (100, 75))
            # 序列化帧
            # pickle.dumps()函数将Python对象转换为字节流，方便通过网络传输
            data = frame.tobytes()  # 直接使用tobytes()方法将帧转换为字节流
            # 基本信息
            length = len(data)
            if len(data) > MAX_DGRAM:
                # 分包逻辑
                chunks = [data[i: i+MAX_DGRAM] for i in range(0, len(data), MAX_DGRAM)]
                for i, chunk in enumerate(chunks):
                    # sock.sendto()是用于发送字节流的
                    # 这里要将帧编号（递增）：2 byte 当前帧内分片序号：2 byte 当前帧总字节数：4 byte加进去
                    chunk = struct.pack(FORMAT, counter, i, length) + chunk
                    sock.sendto(chunk, (UDP_IP, UDP_PORT))
                    # print(f"发送帧 {counter} 分片 {i+1}/{len(chunks)}, 长度 {length} 字节")
                    time.sleep(0.00001)  # 50Hz发送频率
            else:
                data = struct.pack(FORMAT, counter, 0, length) + data
                sock.sendto(data, (UDP_IP, UDP_PORT))
            
            counter += 1
            # print(f"发送帧 {counter}")
        print("准备重新发送视频")
        counter = 0
        time.sleep(1)  # 等待数据发送完成