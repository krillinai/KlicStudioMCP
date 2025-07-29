# KlicStudio MCP 服务器

KlicStudio MCP 服务器是一个基于 Model Context Protocol (MCP) 的连接器，用于与 KlicStudio 服务进行交互。该服务器充当大语言模型 (LLM) 与 KlicStudio 服务之间的桥梁，使 LLM 能够使用 KlicStudio 的字幕生成、翻译、TTS 等功能。

## 功能特点

- **文件上传**: 上传视频或音频文件到 KlicStudio 服务
- **字幕处理**: 为视频自动生成字幕
- **翻译功能**: 支持字幕翻译为多种语言
- **双语字幕**: 生成双语字幕，支持自定义翻译字幕位置
- **文本转语音(TTS)**: 为字幕生成语音，支持音色克隆
- **字幕嵌入**: 将字幕直接嵌入到视频中

## 安装要求

- Python 3.12 或更高版本
- KlicStudio 服务（默认运行在 <http://127.0.0.1:8888）>

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
python KlicStudio-server.py
```
