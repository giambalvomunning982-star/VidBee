"""
情感语录生成模块
使用 OpenAI API 生成符合图片语境的情感语录
"""

import os
from typing import Optional
from openai import OpenAI


class QuoteGenerator:
    """情感语录生成器"""
    
    # 语录风格模板
    QUOTE_STYLES = {
        "emotional": """你是一个情感语录创作专家。请根据以下人物性格特点，创作 {count} 条简短的情感语录。

要求：
- 每条语录 20-50 字
- 风格：温柔治愈、情感共鸣
- 适合搭配美女图片发布在社交媒体
- 用中文创作

性格关键词：{keywords}

请只输出语录，每条用换行分隔：
""",
        "inspirational": """你是一个励志语录创作者。请根据以下人物性格特点，创作 {count} 条励志正能量语录。

要求：
- 每条语录 20-50 字
- 风格：积极向上、激励人心
- 适合搭配美女图片发布在社交媒体
- 用中文创作

性格关键词：{keywords}

请只输出语录，每条用换行分隔：
""",
        "romantic": """你是一个浪漫情感文案创作者。请根据以下人物性格特点，创作 {count} 条浪漫情感语录。

要求：
- 每条语录 20-50 字
- 风格：浪漫唯美、心动感觉
- 适合搭配美女图片发布在社交媒体
- 用中文创作

性格关键词：{keywords}

请只输出语录，每条用换行分隔：
""",
        "philosophical": """你是一个人生感悟创作者。请根据以下人物性格特点，创作 {count} 条人生感悟语录。

要求：
- 每条语录 20-50 字
- 风格：深度思考、人生哲理
- 适合搭配美女图片发布在社交媒体
- 用中文创作

性格关键词：{keywords}

请只输出语录，每条用换行分隔：
"""
    }
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com"
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
    
    def generate_quotes(
        self,
        keywords: str,
        count: int = 5,
        style: str = "emotional",
        model: str = "gpt-3.5-turbo"
    ) -> list[str]:
        """
        生成情感语录
        
        Args:
            keywords: 性格关键词
            count: 生成数量
            style: 语录风格 (emotional, inspirational, romantic, philosophical)
            model: 模型名称
            
        Returns:
            语录列表
        """
        try:
            prompt_template = self.QUOTE_STYLES.get(style, self.QUOTE_STYLES["emotional"])
            prompt = prompt_template.format(count=count, keywords=keywords)
            
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是一个专业的情感语录创作者，擅长写适合社交媒体发布的简短文案。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=1000
            )
            
            quotes_text = response.choices[0].message.content
            
            # 分割语录
            quotes = [q.strip() for q in quotes_text.split("\n") if q.strip()]
            
            return quotes[:count]
            
        except Exception as e:
            print(f"语录生成失败: {e}")
            return self._get_fallback_quotes(keywords, count, style)
    
    def _get_fallback_quotes(self, keywords: str, count: int, style: str) -> list[str]:
        """备用语录生成（API 失败时使用）"""
        fallback_quotes = {
            "emotional": [
                "温柔不是软弱，而是一种选择。在喧嚣的世界裡，保持内心的宁静。",
                "每一个微笑背后，都有不为人知的坚强。",
                "真正的优雅，是历经世事依然温柔以待。",
                "你的温柔，是这个世界上最强大的力量。",
                "在爱别人之前，先学会爱自己。"
            ],
            "inspirational": [
                "每一个优秀的人，都经历过一段沉默的时光。",
                "不是因为看到希望才坚持，而是因为坚持才看到希望。",
                "你的努力，时间都会看得见。",
                "做自己的光，不需要太亮，足以照亮自己就好。",
                "每一次努力，都是对未来的最好准备。"
            ],
            "romantic": [
                "遇见你之前，我没想过未来。遇见你之后，我没想过别人。",
                "有些人的出现，就是为了让你知道，世界依然美好。",
                "最好的爱情，是让你变成最好的自己。",
                "你是我所有的不期而遇，也是我所有的如愿以偿。",
                "世间万般美好，都不及你回眸一笑。"
            ],
            "philosophical": [
                "人生不是等待暴风雨过去，而是学会在雨中跳舞。",
                "真正的成熟，是看透世事依然热爱生活。",
                "每一个现在，都是你以后的回忆。",
                "生活不是等待暴风雨过去，而是学会跳舞。",
                "心若向阳，无畏悲伤。"
            ]
        }
        
        quotes = fallback_quotes.get(style, fallback_quotes["emotional"])
        return quotes[:count]


def match_quote_to_keywords(quotes: list[str], keywords: str) -> dict[str, str]:
    """
    将语录与性格关键词匹配
    
    Args:
        quotes: 语录列表
        keywords: 性格关键词
        
    Returns:
        关键词到语录的映射
    """
    keyword_list = [k.strip() for k in keywords.split(",")]
    matching = {}
    
    for i, kw in enumerate(keyword_list):
        if i < len(quotes):
            matching[kw] = quotes[i]
        else:
            matching[kw] = quotes[i % len(quotes)]
    
    return matching