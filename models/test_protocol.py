from protocol import messages_pb2 as _pb
from typing import cast, Any

_pb = cast(Any, _pb)  # 将_pb强制转换为Any类型，以便在后续代码中使用

# message KeyboardMouseControl {
#     int32 mouse_x = 1;
#     int32 mouse_y = 2;
#     int32 mouse_z = 3;
#     bool left_button_down = 4;
#     bool right_button_down = 5;
#     uint32 keyboard_value = 6;
#     bool mid_button_down = 7;
# }

kbd = _pb.KeyboardMouseControl()


# 核心功能：
# 获取消息名
print("Message Name:", kbd.DESCRIPTOR.name, "\n")  # 输出：KeyboardMouseControl
# 将字典变成消息对象
data_dict = {
    "mouse_x": 100,
    "mouse_y": 200,
    "mouse_z": 300,
    "left_button_down": True,
    "right_button_down": False,
    "keyboard_value": 65,
    "mid_button_down": True
}
kbd2 = _pb.KeyboardMouseControl(**data_dict)
print("KeyboardMouseControl 2:\n", kbd2)  # 输出：mouse_x: 100 mouse_y: 200 mouse_z: 300 left_button_down: true right_button_down: false keyboard_value: 65 mid_button_down: true
# 将消息对象转换为字典
kbd_dict = {}
for field in kbd2.DESCRIPTOR.fields:
    kbd_dict[field.name] = getattr(kbd2, field.name)
print("KeyboardMouseControl Dictionary:\n", kbd_dict)
# 将消息对象转换为字节流
kbd2_bytes = kbd2.SerializeToString()  # 将消息对象转换为字节流
print("Bytes:", kbd2_bytes)  # 输出：b'\x08d\x10\xc8\x01\x18A \x01'
# 从字节流中解析信息
kbd3 = _pb.KeyboardMouseControl()  # 创建一个新的消息对象
kbd3.ParseFromString(kbd2_bytes)  # 解析字节流数据
print("Mouse X:", kbd3.mouse_x)  # 输出：100
# 获取信息对象的json格式数据
from google.protobuf import json_format
kbd_json = json_format.MessageToJson(kbd3)  # 将消息对象转换为json格式数据
print("JSON:", kbd_json)
# 从json格式数据中格式化信息对象
kbd4 = _pb.KeyboardMouseControl()  # 创建一个新的消息对象
json_format.Parse(kbd_json, kbd4)  # 从json格式数据中解析
print("KeyboardMouseControl 4:\n", kbd4)  # 输出：mouse_x: 100 mouse_y: 200 mouse_z: 300 left_button_down: true right_button_down: false keyboard_value: 65 mid_button_down: true

# 核心优化：保留Base类，包含核心6种方法，放弃抽象类设计思想，之后所有信息仅仅只是继承Base类。
# Base类需要继承于protobuf的Message类，包含核心6种方法：获取消息名、将字典变成消息对象、将消息对象转换为字典、将消息对象转换为字节流、从字节流中解析信息、获取信息对象的json格式数据、从json格式数据中格式化信息对象。
