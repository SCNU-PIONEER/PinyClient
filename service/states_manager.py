import sys
sys.path.append("..")  # 添加项目根目录到sys.path，方便导入模块
from models.base import BaseMessage



# class StatesManager:
#     """状态管理器, 顶层设计：用三个大类来统率所有的状态，分别是Game/Robot/Sync，每个大类内部再细分不同的状态"""

#     def __init__(self):
#         # 核心设计：将
#         self.game = RMGame()
#         self.robot = RMRobot()
#         self.sync = RMSync()
#         self.game_topic = self.game.get_all_topics()
#         self.robot_topic = self.robot.get_all_topics()
#         self.sync_topic = self.sync.get_all_topics()


#     def __getitem__(self, key):
#         # 支持两种访问方式：1. game["topic"] 2. game["topic.k"]
#         # 返回BaseMessage对象或者BaseMessage对象的某个字段值
#         if "." in key:
#             topic, k = key.split(".", 1)
#             if topic in self.game_topic:
#                 return self.game[topic][k]
#             elif topic in self.robot_topic:
#                 return self.robot[topic][k]
#             elif topic in self.sync_topic:
#                 return self.sync[topic][k]
#             else:
#                 raise KeyError(f"未知的主题: {topic}")
#         else:
#             if key in self.game_topic:
#                 return self.game[key]
#             elif key in self.robot_topic:
#                 return self.robot[key]
#             elif key in self.sync_topic:
#                 return self.sync[key]
#             else:
#                 raise KeyError(f"未知的主题: {key}")


# if __name__ == "__main__":
#     manager = StatesManager()
#     print(manager["GameStatus.current_round"])
#     print(manager["GameStatus"]["current_round"])