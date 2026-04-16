# tools 目录说明

本目录存放通用工具模块，当前核心工具是日志系统：

- `rm_logger.py`: 统一彩色日志输出与可选文件落盘。

## rm_logger.py 核心逻辑

`RMColorLogger` 封装了 Python `logging`，提供以下能力：

1. 统一日志格式：
   - 时间
   - 级别
   - logger 名称
   - 文件名:行号
   - 消息

2. 分级配色主题：
   - `DEBUG / INFO / WARNING / ERROR / CRITICAL`
   - 不同级别使用不同前景/背景色和样式。

3. 运行时可配置日志级别：
   - 优先读取环境变量 `PIONEER_LOG_LEVEL`
   - 默认读取 `config.py` 中的 `Config.LEVEL`

4. 可选文件日志：
   - 当 `Config.RECORD_LOG=True` 时，按天写入 `Config.LOG_DIR`。
   - 文件名格式：`{logger_name}_YYYY_MM_DD.log`。

5. 调用方位置信息准确：
   - `debug/info/warning/error/critical` 统一设置 `stacklevel=2`，
     让日志中的文件与行号指向业务调用处，而不是 logger 封装内部。

## 使用方式

```python
from tools.rm_logger import RMColorLogger

logger = RMColorLogger("CoreService")
logger.info("服务启动")
logger.error("发生异常")
```

临时调高日志级别（PowerShell）：

```powershell
$env:PIONEER_LOG_LEVEL = "DEBUG"
```

## 维护建议

1. 新增工具模块后，保持“单工具单职责”。
2. 若工具被多模块复用，优先放在 `tools`，避免在 `service`/`models` 重复实现。
3. 日志工具变更后，优先验证：
   - 颜色输出是否正常。
   - 文件落盘路径是否可写。
   - stacklevel 行号是否定位到调用方。
