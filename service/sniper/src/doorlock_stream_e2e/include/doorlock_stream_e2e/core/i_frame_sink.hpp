#pragma once

#include <string>

#include "doorlock_stream_e2e/core/frame_types.hpp"

namespace doorlock_stream_e2e
{

  class IFrameSink
  {
  public:
    virtual ~IFrameSink() = default;

    /// @brief 核心数据流回调
    /// @warning 【极其重要的线程安全契约】
    /// 此回调在底层高频解码线程（50Hz）中被调用！
    /// 实现者（如 Web 后端）必须保证此函数在微秒级内返回。
    /// 绝对禁止在此函数内执行任何阻塞型网络 IO (如 websocket.sync_send)！
    /// 正确做法：将 shared_ptr push 到外部异步队列后立即返回。
    virtual void on_frame(std::shared_ptr<const FrameResult> result) = 0;
    virtual void on_status(StreamStatus status, const std::string &msg = "") = 0;
  };

} // namespace doorlock_stream_e2e
