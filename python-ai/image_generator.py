"""
AI 图片生成模块
支持 OpenAI DALL-E 和 Stable Diffusion 两种生成方式
"""

import os
import base64
import requests
from typing import Optional
from PIL import Image
import io


class OpenAIGenerator:
    """使用 OpenAI DALL-E 生成图片"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com"
    
    def generate(
        self,
        prompt: str,
        style: str = "anime",
        size: str = "512x768",
        model: str = "dall-e-3"
    ) -> Optional[Image.Image]:
        """
        生成图片
        
        Args:
            prompt: 图片描述提示词
            style: 图片风格 (anime, realistic, semi_realistic)
            size: 图片尺寸
            model: 模型名称
            
        Returns:
            PIL.Image 对象，失败返回 None
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            
            # 根据风格调整提示词
            style_prompts = {
                "anime": "anime style, beautiful illustration, high quality, detailed",
                "realistic": "photorealistic, professional photography, high quality, detailed",
                "semi_realistic": "semi-realistic art style, beautiful, high quality, detailed"
            }
            
            enhanced_prompt = f"{prompt}, {style_prompts.get(style, style_prompts['anime'])}"
            
            response = client.images.generate(
                model=model,
                prompt=enhanced_prompt,
                n=1,
                size=size.replace("x", ""),  # DALL-E 3 format
                response_format="b64_json",
                quality="hd" if model == "dall-e-3" else "standard"
            )
            
            image_data = response.data[0].b64_json
            image = Image.open(io.BytesIO(base64.b64decode(image_data)))
            
            return image
            
        except Exception as e:
            print(f"OpenAI 生成失败: {e}")
            return None


class SDGenerator:
    """使用 Stable Diffusion WebUI 生成图片"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:7860"):
        self.base_url = base_url.rstrip("/")
    
    def generate(
        self,
        prompt: str,
        style: str = "anime",
        size: str = "512x768",
        negative_prompt: str = "low quality, blurry, deformed, ugly"
    ) -> Optional[Image.Image]:
        """
        生成图片
        
        Args:
            prompt: 正向提示词
            style: 图片风格
            size: 图片尺寸
            negative_prompt: 反向提示词
            
        Returns:
            PIL.Image 对象，失败返回 None
        """
        try:
            # 根据风格添加标签
            style_tags = {
                "anime": "masterpiece, best quality, anime style, detailed eyes, beautiful face",
                "realistic": "photorealistic, raw photo, professional, detailed skin",
                "semi_realistic": "semi-realistic, digital art, detailed, beautiful"
            }
            
            full_prompt = f"{style_tags.get(style, '')}, {prompt}"
            
            width, height = map(int, size.split("x"))
            
            payload = {
                "prompt": full_prompt,
                "negative_prompt": negative_prompt,
                "steps": 30,
                "cfg_scale": 7,
                "width": width,
                "height": height,
                "batch_size": 1
            }
            
            response = requests.post(
                f"{self.base_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            
            data = response.json()
            image_data = base64.b64decode(data["images"][0])
            image = Image.open(io.BytesIO(image_data))
            
            return image
            
        except Exception as e:
            print(f"Stable Diffusion 生成失败: {e}")
            return None


def create_image_prompt(keywords: str, style: str = "anime") -> str:
    """
    根据性格关键词创建图片生成提示词
    
    Args:
        keywords: 性格关键词，如 "温柔, 独立, 自信"
        style: 图片风格
        
    Returns:
        完整的提示词字符串
    """
    # 风格对应的英文描述
    style_descriptions = {
        "anime": "anime girl, beautiful, detailed illustration",
        "realistic": "beautiful woman, realistic portrait photography",
        "semi_realistic": "beautiful woman, semi-realistic digital art"
    }
    
    # 将中文关键词转换为英文描述
    keyword_translations = {
        "温柔": "gentle and soft expression",
        "独立": "independent and confident posture",
        "自信": "confident smile, strong eyes",
        "活泼": "lively and energetic, bright smile",
        "优雅": "elegant posture, graceful",
        "可爱": "cute and adorable, sweet smile",
        "冷艳": "cool and elegant, mysterious aura",
        "阳光": "sunny and cheerful, warm smile",
        "知性": "intellectual and refined, gentle gaze",
        "神秘": "mysterious and enchanting, deep eyes",
        "活泼": "playful and fun-loving, bright eyes",
        "安静": "quiet and peaceful, serene expression",
        "坚强": "determined and strong, confident stance",
        "善良": "kind and warm, gentle smile",
        "幽默": "humorous and witty, playful expression",
    }
    
    # 构建关键词部分
    keyword_parts = []
    for kw in keywords.split(","):
        kw = kw.strip()
        if kw in keyword_translations:
            keyword_parts.append(keyword_translations[kw])
        else:
            keyword_parts.append(kw)
    
    keyword_desc = ", ".join(keyword_parts)
    
    # 组合完整提示词
    base_desc = style_descriptions.get(style, style_descriptions["anime"])
    prompt = f"{base_desc}, {keyword_desc}, beautiful face, detailed features, full body or portrait"
    
    return prompt


def generate_negative_prompt() -> str:
    """生成负面提示词"""
    return "low quality, worst quality, blurry, deformed, ugly, bad anatomy, disfigured, poorly drawn, extra limbs"