# KlicStudio MCP 服务器

KlicStudio MCP 服务器是一个基于 Model Context Protocol (MCP) 的连接器，用于与 KlicStudio 服务进行交互。该服务器充当大语言模型 (LLM) 与 KlicStudio 服务之间的桥梁，使 LLM 能够使用 KlicStudio 的字幕生成、翻译、TTS 等功能。

## 功能特点

- **文件上传**: 上传视频或音频文件到 KlicStudio 服务
- **字幕处理**: 为视频自动生成字幕，支持多种语言识别
- **翻译功能**: 支持字幕翻译为多种语言
- **双语字幕**: 生成双语字幕，支持自定义翻译字幕位置
- **文本转语音(TTS)**: 为字幕生成语音，支持音色克隆
- **字幕嵌入**: 将字幕直接嵌入到视频中，支持横屏和竖屏视频
- **配置管理**: 动态获取和更新 KlicStudio 系统配置
- **任务监控**: 实时查询字幕处理任务状态和进度

## 安装要求

- Python 3.12 或更高版本
- KlicStudio 服务（默认运行在 http://127.0.0.1:8888）

## 安装

```bash
# 克隆仓库
git clone git@github.com:krillinai/KlicStudioMCP.git
cd KlicStudioMCP

# 使用 pip 安装依赖
pip install -e .

# 或者使用 uv 安装（推荐）
uv pip install -e .
```

## 使用方法

### 启动服务器

```bash
python klicstudio-mcp.py
```

### 与 MCP 客户端集成

#### Claude Desktop 示例配置

要将此服务器集成到 Claude Desktop，您需要编辑其 MCP 服务器配置文件。 在 macOS 上，该文件通常位于`~/Library/Application Support/Claude/claude_desktop_config.json`。

```json
{
  "mcpServers": {
    "KlicStudio-mcp-server": {
      "isActive": true,
      "name": "KlicStudioConnector", 
      "type": "stdio",
      "description": "Connects to KlicStudio for subtitle and media processing.",
      "command": "/abs/path/to/your/project/.venv/bin/python",
      "args": [
        "/abs/path/to/your/project/klicstudio-mcp.py" 
      ],
      "env": {}
    }
  }
}
```

**请务必将** **`/abs/path/to/your/project/` 替换为您的实际项目路径。**

### 命令行选项

- `--klicstudio-url`: 指定 KlicStudio 服务的 URL (默认: http://127.0.0.1:8888)
- `--mcp-transport`: 指定 MCP 传输类型，可选 "stdio"(默认) 或 "streamable-http"
- `--mcp-host`: 指定 HTTP 服务器主机（仅当 mcp-transport 为 "streamable-http" 时有效）
- `--mcp-port`: 指定 HTTP 服务器端口（仅当 mcp-transport 为 "streamable-http" 时有效）

示例:

```bash
# 使用环境变量设置 KlicStudio URL
export KLICSTUDIO_URL="http://192.168.1.100:8888"
python klicstudio-mcp.py

# 或者直接通过命令行参数设置
python klicstudio-mcp.py --klicstudio-url="http://192.168.1.100:8888"

# 使用 HTTP 传输并指定端口
python klicstudio-mcp.py --mcp-transport="streamable-http" --mcp-port=8001
```

## MCP 工具

该服务器提供了以下 MCP 工具供 LLM 使用：

### 1. 配置管理工具

- `get_klicstudio_base_url`: 获取当前 KlicStudio 连接器配置
- `set_klicstudio_base_url`: 设置 KlicStudio 服务的 BASE URL
- `get_klicstudio_system_config`: 获取 KlicStudio 系统的完整配置信息
- `update_klicstudio_system_config`: 更新 KlicStudio 系统配置
- `update_klicstudio_llm_config`: 快速更新 LLM 配置（便捷方法）

### 2. 文件处理工具

- `upload_file_to_klicstudio`: 将服务器可访问的文件上传到 KlicStudio

### 3. 字幕处理工具

- `start_klicstudio_subtitle_task`: 启动字幕处理任务
- `get_klicstudio_subtitle_task_details`: 获取字幕任务详情

### 4. 内容获取工具

- `fetch_klicstudio_file_as_text`: 获取 KlicStudio 文件的文本内容

## 工作流程示例

1. **上传视频文件**: 使用 `upload_file_to_klicstudio` 上传视频到 KlicStudio 服务
2. **启动字幕处理任务**: 使用 `start_klicstudio_subtitle_task` 启动字幕处理，可设置：
   - 源语言和目标语言
   - 是否生成双语字幕
   - 是否启用 TTS 和音色克隆
   - 是否嵌入字幕到视频
3. **监控任务进度**: 使用 `get_klicstudio_subtitle_task_details` 查询任务状态直至完成
4. **获取处理结果**: 下载生成的字幕文件、语音或嵌入字幕的视频

## 高级功能

### 字幕嵌入选项
- `horizontal`: 仅生成横屏嵌入字幕视频
- `vertical`: 仅生成竖屏嵌入字幕视频  
- `all`: 生成横屏和竖屏两种嵌入字幕视频
- `none`: 不生成嵌入字幕视频（默认）

### TTS 音色克隆
支持使用上传的音频文件进行音色克隆，生成更自然的语音输出。

### 词语替换
支持自定义词语替换规则，格式为 `["原词1|替换词1", "原词2|替换词2", ...]`

### 语气词过滤
可选择是否过滤语气词等，提高字幕质量。
   

