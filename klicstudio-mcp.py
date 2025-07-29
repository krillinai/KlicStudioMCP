# klicstudio_server.py
"""
KlicStudio MCP 服务器
提供与 KlicStudio 字幕处理服务的集成接口

功能模块：
- 配置管理：获取和设置 KlicStudio 系统配置
- 文件管理：上传文件到 KlicStudio 服务
- 字幕任务：启动和查询字幕处理任务
- 工具函数：下载文件内容等辅助功能
"""

import httpx
import os
import base64
import mimetypes
import argparse
from typing import Optional, List, Union, Dict, Any, Literal

from mcp.server.fastmcp import FastMCP, Context

# ===== 全局配置 =====
KLICSTUDIO_BASE_URL: str = "http://127.0.0.1:8888"

# 创建 FastMCP 服务器实例
mcp = FastMCP("KlicStudioConnector")

# ===== 类型定义 =====
SourceLanguage = Literal["zh_cn", "en", "ja", "tr", "de", "ko", "ru"]

TranslationLanguage = Literal[
    "zh_cn", "zh_tw", "en", "ja", "pinyin", "mid", "ms", "th", "vi", "fil", 
    "ko", "ar", "fr", "de", "it", "ru", "pt", "es", "hi", "bn", "he", "fa", 
    "af", "sv", "fi", "da", "no", "nl", "el", "uk", "hu", "pl", "tr", "sr", 
    "hr", "cs", "sw", "yo", "ha", "am", "om", "is", "lb", "ca", "ro", "ro2", 
    "sk", "bs", "mk", "sl", "bg", "lv", "lt", "et", "mt", "sq"
]

# ===== 辅助函数 =====
async def _klicstudio_request(method: str, endpoint: str, **kwargs) -> httpx.Response:
    """统一处理对 KlicStudio API 的请求"""
    async with httpx.AsyncClient(timeout=120.0) as client:
        url = f"{KLICSTUDIO_BASE_URL}{endpoint}"
        
        log_kwargs = {k: v for k, v in kwargs.items() if k != "files"} 
        print(f"向 KlicStudio 发起请求: {method} {url} with {log_kwargs}")

        try:
            if method.upper() == "GET":
                response = await client.get(url, **kwargs)
            elif method.upper() == "POST":
                response = await client.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            print(f"KlicStudio API HTTP Error for {method} {url}: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            print(f"KlicStudio API Request Error for {method} {url}: {str(e)}")
            raise
        except Exception as e:
            print(f"Unexpected error during KlicStudio API call for {method} {url}: {str(e)}")
            raise

# --- MCP 工具集合 ---

# ===== 1. 配置管理工具 =====
@mcp.tool()
async def get_klicstudio_base_url(ctx: Context) -> dict:
    """
    获取当前 KlicStudio 连接器配置，主要是 KlicStudio 服务的 BASE URL。
    """
    global KLICSTUDIO_BASE_URL
    ctx.info(f"获取当前 KlicStudio BASE URL: {KLICSTUDIO_BASE_URL}")
    return {
        "error": 0,
        "msg": "当前配置获取成功",
        "data": {
            "klicstudio_base_url": KLICSTUDIO_BASE_URL
        }
    }

@mcp.tool()
async def set_klicstudio_base_url(ctx: Context, new_url: str) -> dict:
    """
    设置 KlicStudio 服务的 BASE URL。
    注意: 此更改将影响当前 MCP 服务器实例后续所有对 KlicStudio 的调用。

    Args:
        new_url: 新的 KlicStudio 服务 BASE URL (例如 "http://localhost:8889" 或 "http://remote.klicstudio.server").
                 请确保 URL 格式正确且服务可达。
    """
    global KLICSTUDIO_BASE_URL
    previous_url = KLICSTUDIO_BASE_URL
    
    if not (new_url.startswith("http://") or new_url.startswith("https://")):
        msg = "设置失败：URL 格式不正确，应以 http:// 或 https:// 开头。"
        ctx.error(msg)
        return {"error": 1, "msg": msg, "data": {"previous_url": previous_url}}

    KLICSTUDIO_BASE_URL = new_url.rstrip('/') # 存储时移除末尾斜杠
    msg = f"KlicStudio BASE URL 已从 '{previous_url}' 更新为 '{KLICSTUDIO_BASE_URL}'。"
    ctx.info(msg)
    return {
        "error": 0,
        "msg": msg,
        "data": {
            "new_klicstudio_base_url": KLICSTUDIO_BASE_URL,
            "previous_klicstudio_base_url": previous_url
        }
    }

@mcp.tool()
async def get_klicstudio_system_config(ctx: Context) -> dict:
    """
    获取 KlicStudio 系统的完整配置信息，包括应用、服务器、LLM、转录和TTS等配置。
    """
    try:
        ctx.info("获取 KlicStudio 系统配置...")
        response = await _klicstudio_request("GET", "/api/config")
        klicstudio_response = response.json()
        ctx.info("KlicStudio 系统配置获取成功")
        return klicstudio_response
    except Exception as e:
        ctx.error(f"获取 KlicStudio 系统配置失败: {str(e)}")
        return {"error": 1, "msg": f"获取系统配置失败: {str(e)}", "data": None}

@mcp.tool()
async def update_klicstudio_system_config(ctx: Context, config_data: dict) -> dict:
    """
    更新 KlicStudio 系统配置。配置将被验证并保存到配置文件。
    
    Args:
        config_data: 完整的配置数据字典，包含以下结构：
                    {
                      "app": {
                        "segmentDuration": int,
                        "transcribeParallelNum": int,
                        "translateParallelNum": int,
                        "transcribeMaxAttempts": int,
                        "translateMaxAttempts": int,
                        "maxSentenceLength": int,
                        "proxy": string
                      },
                      "server": {
                        "host": string,
                        "port": int
                      },
                      "llm": {
                        "baseUrl": string,
                        "apiKey": string,
                        "model": string
                      },
                      "transcribe": {
                        "provider": string,
                        "enableGpuAcceleration": bool,
                        "openai": {...},
                        "fasterwhisper": {...},
                        "whisperkit": {...},
                        "whispercpp": {...},
                        "aliyun": {...}
                      },
                      "tts": {
                        "provider": string,
                        "openai": {...},
                        "aliyun": {...}
                      }
                    }
    Returns:
        包含更新结果的字典，成功时 error=0，失败时包含错误信息。
    """
    try:
        ctx.info("准备更新 KlicStudio 系统配置...")
        ctx.info(f"配置数据: {config_data}")
        
        response = await _klicstudio_request("POST", "/api/config", json=config_data)
        klicstudio_response = response.json()
        
        if klicstudio_response.get("error") == 0:
            ctx.info("KlicStudio 系统配置更新成功")
        else:
            ctx.error(f"KlicStudio 系统配置更新失败: {klicstudio_response.get('msg', '未知错误')}")
            
        return klicstudio_response
    except Exception as e:
        ctx.error(f"更新 KlicStudio 系统配置失败: {str(e)}")
        return {"error": 1, "msg": f"更新系统配置失败: {str(e)}", "data": None}

@mcp.tool()
async def update_klicstudio_llm_config(
    ctx: Context,
    base_url: str,
    api_key: str,
    model: str
) -> dict:
    """
    快速更新 KlicStudio 的 LLM 配置。这是一个便捷方法，只更新 LLM 相关配置。
    
    Args:
        base_url: LLM API 的基础 URL
        api_key: LLM API 的密钥
        model: 要使用的模型名称
    Returns:
        包含更新结果的字典
    """
    try:
        # 先获取当前配置
        current_config_response = await get_klicstudio_system_config(ctx)
        if current_config_response.get("error") != 0:
            return current_config_response
            
        # 更新 LLM 部分
        config_data = current_config_response["data"]
        config_data["llm"]["baseUrl"] = base_url
        config_data["llm"]["apiKey"] = api_key
        config_data["llm"]["model"] = model
        
        # 提交更新
        return await update_klicstudio_system_config(ctx, config_data)
        
    except Exception as e:
        ctx.error(f"快速更新 LLM 配置失败: {str(e)}")
        return {"error": 1, "msg": f"更新 LLM 配置失败: {str(e)}", "data": None}

# ===== 2. 文件管理工具 =====
@mcp.tool()
async def upload_file_to_klicstudio(ctx: Context, server_accessible_file_path: str) -> dict:
    """
    将 MCP 服务器可访问路径下的文件上传到 KlicStudio 服务。
    可用于上传视频进行字幕处理，或上传音频进行音色克隆。

    Args:
        server_accessible_file_path: 文件在 MCP 服务器文件系统上的绝对路径。
                                     LLM 需要确保文件已通过某种方式放置在此路径。
    Returns:
        一个包含 KlicStudio 服务上文件路径的字典，或错误信息。
    """
    try:
        if not os.path.exists(server_accessible_file_path):
            return {"error": 1, "msg": f"文件未找到: {server_accessible_file_path}", "data": None}
        
        file_name = os.path.basename(server_accessible_file_path)
        
        with open(server_accessible_file_path, "rb") as f:
            file_content = f.read()
            
        mime_type, _ = mimetypes.guess_type(server_accessible_file_path)
        if mime_type is None:
            if file_name.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                mime_type = 'video/mp4' # 常用视频MIME
            elif file_name.lower().endswith(('.mp3', '.wav', '.aac', '.m4a')):
                mime_type = 'audio/mpeg' # 常用音频MIME
            else:
                mime_type = 'application/octet-stream'
            
        files_param = {"file": (file_name, file_content, mime_type)}
        
        ctx.info(f"准备上传文件: {file_name} (MIME: {mime_type}) 到 KlicStudio...")
        response = await _klicstudio_request("POST", "/api/file", files=files_param)
        klicstudio_response = response.json()
        ctx.info(f"KlicStudio 文件上传响应: {klicstudio_response}")
        if klicstudio_response.get("data") and isinstance(klicstudio_response["data"].get("file_path"), str):
            klicstudio_response["data"]["file_path"] = klicstudio_response["data"]["file_path"][0]

        return klicstudio_response
            
    except Exception as e:
        ctx.error(f"上传文件到 KlicStudio 失败: {str(e)}")
        return {"error": 1, "msg": f"上传文件失败: {str(e)}", "data": None}

# ===== 3. 字幕任务工具 =====
@mcp.tool()
async def start_klicstudio_subtitle_task(
    ctx: Context,
    media_url_on_klicstudio: str,
    language: str = "zh_cn",
    origin_lang: Optional[str] = None,
    target_lang: Optional[str] = None,
    bilingual: bool = False,
    translation_subtitle_pos: Literal[1, 2] = 1,
    tts: bool = False,
    tts_voice_code: Optional[Literal[1, 2]] = None,
    tts_voice_clone_src_file_url: Optional[str] = None,
    modal_filter: bool = False,
    embed_subtitle_video_type: Literal["horizontal", "vertical", "all", "none"] = "none",
    vertical_major_title: Optional[str] = None,
    vertical_minor_title: Optional[str] = None,
    replace_words: Optional[List[str]] = None
) -> dict:
    """
    为 KlicStudio 服务上已上传的媒体文件或外部链接启动字幕处理任务。

    Args:
        media_url_on_klicstudio: KlicStudio 服务上的媒体文件路径 (例如 "local:./uploads/video.mp4") 或可访问的外部媒体链接。
        language: 媒体内容的源语言或主要识别语言。
                  可选值: "zh_cn" (简体中文), "en" (英文), "ja" (日文), "tr" (土耳其语), "de" (德语), "ko" (韩语), "ru" (俄语)。
                  默认为 "zh_cn"。
        origin_lang: 可选，进行翻译时的源语言。如果启用翻译且未提供此项，可能默认为 `language` 参数的值。
                     可选值同 `language` 参数。
        target_lang: 可选，进行翻译时的目标语言。如果提供了此参数，表示需要翻译。
                     可用值非常广泛，例如 "zh_cn", "zh_tw", "en", "ja", "pinyin", "fr", "es", "de" 等。
        bilingual: 是否生成双语字幕。True 表示启用 (发送 1 给 KlicStudio)，False 表示不启用 (发送 2 给 KlicStudio)。默认为 False。
        translation_subtitle_pos: 双语字幕时，翻译字幕的位置。1 = 翻译字幕在上, 2 = 翻译字幕在下。默认为 1。
        tts: 是否为字幕启用 TTS (文本转语音)。True 表示启用 (发送 1 给 KlicStudio)，False 表示不启用 (发送 2 给 KlicStudio)。默认为 False。
        tts_voice_code: 可选，TTS 使用的音色代码。例如 en-US-SteffanNeural / xiaoyun 。
        tts_voice_clone_src_file_url: 可选，用于 TTS 音色克隆的已上传音频文件在 KlicStudio 上的路径。
        modal_filter: 是否过滤语气词等。True 表示启用 (发送 1 给 KlicStudio)，False 表示不启用 (发送 2 给 KlicStudio)。默认为 False。
        embed_subtitle_video_type: 字幕嵌入视频的类型。
                                   可选值: "horizontal", "vertical", "all", "none"。默认为 "none"。
        vertical_major_title: 可选，当 embed_subtitle_video_type 为 "vertical" 或 "all" 时，竖屏视频的主标题。
        vertical_minor_title: 可选，当 embed_subtitle_video_type 为 "vertical" 或 "all" 时，竖屏视频的副标题。
        replace_words: 可选，词语替换列表，格式为 ["原词1|替换词1", "原词2|替换词2", ...]。

    Returns:
        一个包含任务 ID 的字典，或错误信息。
    """
    try:
        payload: Dict[str, Any] = {
            "url": media_url_on_klicstudio,
            "language": language,
            "bilingual": 1 if bilingual else 2,
            "translation_subtitle_pos": translation_subtitle_pos,
            "tts": 1 if tts else 2,
            "modal_filter": 1 if modal_filter else 2,
            "embed_subtitle_video_type": embed_subtitle_video_type,
        }
        if origin_lang:
            payload["origin_lang"] = origin_lang
        else:
            if target_lang: # 只有在需要翻译时，才考虑默认origin_lang
                 payload["origin_lang"] = language

        if target_lang:
            payload["target_lang"] = target_lang
        
        if payload["tts"] == 1: # 只有当 tts 实际要发送为 1 (启用) 时，才处理 tts 相关子参数
            if tts_voice_code is not None:
                payload["tts_voice_code"] = tts_voice_code
            if tts_voice_clone_src_file_url:
                payload["tts_voice_clone_src_file_url"] = tts_voice_clone_src_file_url
        
        if vertical_major_title is not None:
            payload["vertical_major_title"] = vertical_major_title
        if vertical_minor_title is not None:
            payload["vertical_minor_title"] = vertical_minor_title
        if replace_words:
            payload["replace"] = replace_words
            
        ctx.info(f"向 KlicStudio 启动字幕任务，参数: {payload}")
        response = await _klicstudio_request("POST", "/api/capability/subtitleTask", json=payload)
        klicstudio_response = response.json()
        ctx.info(f"KlicStudio 字幕任务启动响应: {klicstudio_response}")
        return klicstudio_response
    except Exception as e:
        ctx.error(f"启动 KlicStudio 字幕任务失败: {str(e)}")
        return {"error": 1, "msg": f"启动字幕任务失败: {str(e)}", "data": None}

@mcp.tool()
async def get_klicstudio_subtitle_task_details(ctx: Context, task_id: str) -> dict:
    """
    获取 KlicStudio 字幕任务的当前状态、进度和结果（如果已完成）。
    如果任务完成且可能生成了嵌入字幕的视频，会尝试添加这些视频的潜在下载链接。

    Args:
        task_id: 要查询的任务 ID。
    Returns:
        一个包含任务详细信息的字典，包括状态、进度、字幕/语音下载链接，以及可能的嵌入字幕视频链接。
    """
    try:
        ctx.info(f"查询 KlicStudio 字幕任务详情，Task ID: {task_id}")
        response = await _klicstudio_request("GET", f"/api/capability/subtitleTask?taskId={task_id}")
        klicstudio_response = response.json()
        
        # 修改响应中的数据，添加完整的下载链接
        if klicstudio_response.get("error") == 0 and "data" in klicstudio_response:
            data_part = klicstudio_response["data"]
            
            progress = data_part.get("process_percent")
            ctx.info(f"KlicStudio 任务 '{task_id}' 状态: progress {progress if progress is not None else '未知'}%")
            
            # 确保 subtitle_info 中的下载链接是完整的 URL
            if "subtitle_info" in data_part and isinstance(data_part["subtitle_info"], list):
                for item in data_part["subtitle_info"]:
                    if "download_url" in item and isinstance(item["download_url"], str) and not item["download_url"].startswith("http"):
                        relative_url = item["download_url"]
                        item["download_url"] = f"{KLICSTUDIO_BASE_URL.rstrip('/')}{relative_url}" if relative_url.startswith("/") else f"{KLICSTUDIO_BASE_URL.rstrip('/')}/{relative_url}"
            
            # 确保 speech_download_url 是完整的 URL
            if "speech_download_url" in data_part and isinstance(data_part["speech_download_url"], str) and data_part["speech_download_url"] and not data_part["speech_download_url"].startswith("http"):
                relative_url = data_part["speech_download_url"]
                data_part["speech_download_url"] = f"{KLICSTUDIO_BASE_URL.rstrip('/')}{relative_url}" if relative_url.startswith("/") else f"{KLICSTUDIO_BASE_URL.rstrip('/')}/{relative_url}"

            # 如果任务完成，添加嵌入字幕视频的推断下载链接
            if progress == 100:
                if "potential_embedded_video_urls" not in data_part:
                    data_part["potential_embedded_video_urls"] = []
                
                # 横屏视频链接
                h_embed_path = f"/api/file/tasks/{task_id}/output/horizontal_embed.mp4"
                data_part["potential_embedded_video_urls"].append({
                    "name": "嵌入字幕的横屏视频 (可能存在)",
                    "download_url": f"{KLICSTUDIO_BASE_URL.rstrip('/')}{h_embed_path}"
                })
                
                # 竖屏视频链接
                v_embed_path = f"/api/file/tasks/{task_id}/output/vertical_embed.mp4"
                data_part["potential_embedded_video_urls"].append({
                    "name": "嵌入字幕的竖屏视频 (可能存在)",
                    "download_url": f"{KLICSTUDIO_BASE_URL.rstrip('/')}{v_embed_path}"
                })
                ctx.info(f"为已完成的任务 {task_id} 添加了推断的嵌入视频下载链接。")
        
        return klicstudio_response
    
    except Exception as e:
        error_msg = f"获取 KlicStudio 字幕任务详情失败 (ID: {task_id}): {str(e)}"
        ctx.error(error_msg)
        return {"error": 1, "msg": error_msg, "data": {"task_id": task_id}}

# ===== 4. 实用工具 =====
@mcp.tool()
async def fetch_klicstudio_file_as_text(ctx: Context, full_download_url: str) -> dict:
    """
    根据 KlicStudio 提供的完整 URL 下载文件内容，并以文本形式返回。
    适用于字幕文件等小型文本文件。

    Args:
        full_download_url: KlicStudio 任务结果中提供的完整可下载 HTTP/HTTPS URL。
    Returns:
        一个包含文件名、文本内容和MIME类型的字典，或错误信息。
    """
    try:
        ctx.info(f"准备从 KlicStudio 下载并获取文本内容: {full_download_url}")
        
        # 这里不再需要 _klicstudio_request，因为它是完整的外部 URL
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(full_download_url)
            response.raise_for_status()
        
        file_content_bytes = response.content
        # 尝试将内容解码为 UTF-8 文本，对于 SRT 等字幕文件通常是这样
        try:
            file_text_content = file_content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # 如果 UTF-8 解码失败，可以尝试其他编码或直接返回错误
            ctx.warning(f"文件 {full_download_url} UTF-8 解码失败，尝试 Latin-1")
            try:
                file_text_content = file_content_bytes.decode("latin-1")
            except UnicodeDecodeError:
                return {"error": 1, "msg": "文件内容无法解码为文本", "data": None}

        file_name = os.path.basename(httpx.URL(full_download_url).path)
        mime_type = response.headers.get("content-type", "text/plain")

        ctx.info(f"文件 {file_name} (MIME: {mime_type}) 内容获取成功，长度: {len(file_content_bytes)} bytes.")
        return {
            "error": 0,
            "msg": "文件内容获取成功",
            "data": {
                "file_name": file_name,
                "text_content": file_text_content,
                "mime_type": mime_type,
            }
        }
    except Exception as e:
        ctx.error(f"从 KlicStudio URL 下载文件内容失败 ({full_download_url}): {str(e)}")
        return {"error": 1, "msg": f"下载文件内容失败: {str(e)}", "data": None}

# ===== 主程序入口 =====
if __name__ == "__main__":
    # 默认的 KlicStudio URL
    DEFAULT_KLICSTUDIO_URL = "http://127.0.0.1:8888"

    parser = argparse.ArgumentParser(description="MCP Server for KlicStudio Connector")
    parser.add_argument(
        "--klicstudio-url",
        type=str,
        default=os.getenv("KLICSTUDIO_URL", DEFAULT_KLICSTUDIO_URL),
        help=f"The base URL for the KlicStudio service (e.g., http://localhost:8888). "
             f"Can also be set via KLICSTUDIO_URL environment variable. Default: {DEFAULT_KLICSTUDIO_URL}"
    )
    parser.add_argument(
        "--mcp-transport",
        type=str,
        default="stdio",
        choices=["stdio", "streamable-http"],
        help="MCP transport type to use (default: stdio)"
    )
    parser.add_argument(
        "--mcp-host",
        type=str,
        default="0.0.0.0",
        help="Host for streamable-http transport (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=8001,
        help="Port for streamable-http transport (default: 8001)"
    )

    args = parser.parse_args()

    KLICSTUDIO_BASE_URL = args.klicstudio_url.rstrip('/')

    print(f"KlicStudio MCP 服务器启动中...")
    print(f"  将连接到 KlicStudio 服务于: {KLICSTUDIO_BASE_URL}")
    print(f"  MCP Transport 类型: {args.mcp_transport}")
    
    if args.mcp_transport == "streamable-http":
        print(f"  MCP 服务将监听于: {args.mcp_host}:{args.mcp_port}/mcp")
        mcp.settings.host = args.mcp_host
        mcp.settings.port = args.mcp_port
    
    mcp.run(transport=args.mcp_transport)
 