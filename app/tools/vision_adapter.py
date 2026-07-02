import json
import os
import re
import urllib.request
import urllib.error
from typing import Any, Dict, Optional


def _lower(text: str) -> str:
    return (text or "").lower()


def extract_image_url_from_message(message: str) -> Optional[str]:
    """
    从用户文本里提取图片 URL。
    例如：
    我的戒指有问题，图片：https://example.com/ring_damage.jpg
    """
    if not message:
        return None

    pattern = r"(https?://[^\s，。；;]+(?:\.jpg|\.jpeg|\.png|\.webp)(?:\?[^\s，。；;]+)?)"
    m = re.search(pattern, message, re.IGNORECASE)

    if m:
        return m.group(1)

    return None


def mock_vision_from_url(message: str, image_url: str) -> Dict[str, Any]:
    """
    Mock Vision Adapter。

    作用：
    1. 没有真实多模态 API Key 时，保证项目可运行；
    2. 根据 image_url 文件名和用户文本模拟识别结果；
    3. 用于开发、演示和离线测试。

    注意：
    这不是最终真实图片像素识别，而是开发环境的 Mock Adapter。
    """
    text = _lower(f"{message} {image_url}")

    high_keywords = [
        "missing", "stone", "broken", "crack", "damage", "damaged", "severe",
        "掉钻", "缺石", "断裂", "裂开", "破损", "损坏", "严重"
    ]

    medium_keywords = [
        "scratch", "fading", "oxidation", "color", "worn",
        "划痕", "刮痕", "褪色", "氧化", "色差", "发黑"
    ]

    if any(k in text for k in high_keywords):
        summary = (
            "Damage summary: has_image: true; visible_issue: yes; "
            "damage_type: missing_stone; severity: high; "
            "summary: The jewelry image appears to show a missing stone, breakage, "
            "or damaged setting area."
        )
        return {
            "success": True,
            "mode": "mock",
            "has_image": True,
            "visible_issue": "yes",
            "damage_type": "missing_stone_or_breakage",
            "severity": "high",
            "vision_summary": summary,
            "note": "Mock mode result generated from image_url/message keywords."
        }

    if any(k in text for k in medium_keywords):
        summary = (
            "Damage summary: has_image: true; visible_issue: yes; "
            "damage_type: scratch_or_color_issue; severity: medium; "
            "summary: The jewelry image appears to show surface scratches, fading, "
            "oxidation, or color difference."
        )
        return {
            "success": True,
            "mode": "mock",
            "has_image": True,
            "visible_issue": "yes",
            "damage_type": "scratch_or_color_issue",
            "severity": "medium",
            "vision_summary": summary,
            "note": "Mock mode result generated from image_url/message keywords."
        }

    summary = (
        "Damage summary: has_image: true; visible_issue: unclear; "
        "damage_type: unclear; severity: low; "
        "summary: The image is available, but no clear jewelry damage can be "
        "confirmed from the provided context."
    )

    return {
        "success": True,
        "mode": "mock",
        "has_image": True,
        "visible_issue": "unclear",
        "damage_type": "unclear",
        "severity": "low",
        "vision_summary": summary,
        "note": "Mock mode result generated from image_url/message keywords."
    }


def call_openai_compatible_vision(message: str, image_url: str) -> Dict[str, Any]:
    """
    通用 OpenAI-compatible Vision Adapter。

    需要环境变量：
    VISION_API_URL
    VISION_API_KEY
    VISION_MODEL

    例如后续你可以接：
    - qwen-vl 系列兼容接口
    - gpt-4o / gpt-4o-mini 兼容接口
    - 其他支持 image_url 的多模态模型接口

    如果没有配置环境变量，本函数会返回错误，不影响 Mock 模式。
    """
    api_url = os.getenv("VISION_API_URL", "").strip()
    api_key = os.getenv("VISION_API_KEY", "").strip()
    model = os.getenv("VISION_MODEL", "qwen-vl-plus").strip()

    if not api_url or not api_key:
        return {
            "success": False,
            "mode": "openai_compatible",
            "error": "VISION_API_URL or VISION_API_KEY is not configured."
        }

    prompt = """
You are JewelryCare AI's after-sales image triage assistant.

Please inspect the jewelry image and summarize visible after-sales issues.

Focus on:
1. missing stones or damaged setting;
2. broken, cracked, deformed parts;
3. scratches, fading, oxidation, color difference;
4. unclear or insufficient evidence.

Return only this English format:

Damage summary:
- has_image: true / false
- visible_issue: yes / no / unclear
- damage_type: missing_stone / broken / scratch / fading / oxidation / unclear
- severity: low / medium / high
- summary: one short English sentence

Do not promise refund, replacement, compensation, or final quality judgment.
"""

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"{prompt}\n\nCustomer message:\n{message}"
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url
                        }
                    }
                ]
            }
        ],
        "temperature": 0.1
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            data = json.loads(raw)

        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )

        if isinstance(content, list):
            content = "\n".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )

        return {
            "success": True,
            "mode": "openai_compatible",
            "model": model,
            "vision_summary": content,
            "raw": data
        }

    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="ignore")
        return {
            "success": False,
            "mode": "openai_compatible",
            "error": f"HTTPError {e.code}",
            "detail": body
        }
    except Exception as e:
        return {
            "success": False,
            "mode": "openai_compatible",
            "error": type(e).__name__,
            "detail": str(e)
        }


def analyze_image_url(message: str, image_url: Optional[str]) -> Dict[str, Any]:
    """
    Vision Adapter 总入口。

    VISION_MODE=mock                默认 Mock 模式
    VISION_MODE=openai_compatible   调用真实多模态模型
    """
    if not image_url:
        image_url = extract_image_url_from_message(message or "")

    if not image_url:
        return {
            "success": True,
            "mode": "no_image",
            "has_image": False,
            "vision_summary": "",
            "message": "No image_url provided."
        }

    mode = os.getenv("VISION_MODE", "mock").strip().lower()

    if mode == "openai_compatible":
        result = call_openai_compatible_vision(message=message, image_url=image_url)

        # 如果真实视觉接口失败，不自动伪造识别结果，但返回错误方便调试。
        if result.get("success"):
            result["image_url"] = image_url
            return result

        result["image_url"] = image_url
        return result

    result = mock_vision_from_url(message=message, image_url=image_url)
    result["image_url"] = image_url
    return result
