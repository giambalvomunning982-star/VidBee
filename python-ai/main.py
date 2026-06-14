"""
AI 美女图片+情感语录自动生成器

功能：
1. 根据性格关键词生成系列化美女/动漫图片
2. 为每张图片生成符合语境的情感语录
3. 自动打包输出，适合社交媒体发布

用法：
    python main.py --keywords "温柔,独立,自信" --count 5 --style anime
    python main.py --keywords "活泼,阳光,可爱" --count 3 --style realistic
"""

import os
import argparse
import datetime
from pathlib import Path
from dotenv import load_dotenv

from image_generator import (
    OpenAIGenerator,
    SDGenerator,
    create_image_prompt,
    generate_negative_prompt
)
from quote_generator import QuoteGenerator


class AIGenerator:
    """AI 图片+语录生成主类"""
    
    def __init__(self, config: dict):
        """
        初始化生成器
        
        Args:
            config: 配置字典
        """
        self.config = config
        self.output_dir = config.get("output_dir", "output")
        self.style = config.get("style", "anime")
        self.image_size = config.get("image_size", "512x768")
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 初始化生成器
        self.image_gen = self._init_image_generator()
        self.quote_gen = self._init_quote_generator()
    
    def _init_image_generator(self):
        """初始化图片生成器"""
        generator_type = self.config.get("generator_type", "openai")
        
        if generator_type == "openai":
            api_key = self.config.get("openai_api_key")
            base_url = self.config.get("openai_base_url")
            if not api_key:
                raise ValueError("使用 OpenAI 需要提供 OPENAI_API_KEY")
            return OpenAIGenerator(api_key, base_url)
        
        elif generator_type == "stable_diffusion":
            base_url = self.config.get("sd_webui_url", "http://127.0.0.1:7860")
            return SDGenerator(base_url)
        
        else:
            raise ValueError(f"不支持的生成器类型: {generator_type}")
    
    def _init_quote_generator(self):
        """初始化语录生成器"""
        api_key = self.config.get("openai_api_key")
        base_url = self.config.get("openai_base_url")
        if not api_key:
            raise ValueError("使用语录生成需要提供 OPENAI_API_KEY")
        return QuoteGenerator(api_key, base_url)
    
    def generate(self, keywords: str, count: int = 5, quote_style: str = "emotional") -> dict:
        """
        生成图片和语录
        
        Args:
            keywords: 性格关键词，用逗号分隔
            count: 生成数量
            quote_style: 语录风格 (emotional, inspirational, romantic, philosophical)
            
        Returns:
            包含生成结果的字典
        """
        print(f"\n{'='*50}")
        print(f"开始生成 - 关键词: {keywords}")
        print(f"数量: {count}, 风格: {self.style}")
        print(f"{'='*50}\n")
        
        # 创建本次生成的子目录
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        keyword_short = keywords.replace(",", "_")[:20]
        sub_dir = os.path.join(self.output_dir, f"{keyword_short}_{timestamp}")
        os.makedirs(sub_dir, exist_ok=True)
        
        results = {
            "keywords": keywords,
            "count": count,
            "style": self.style,
            "quote_style": quote_style,
            "output_dir": sub_dir,
            "images": [],
            "quotes": []
        }
        
        # 生成图片提示词
        image_prompt = create_image_prompt(keywords, self.style)
        print(f"图片提示词: {image_prompt[:100]}...")
        
        # 生成图片
        print("\n正在生成图片...")
        for i in range(count):
            print(f"  [{i+1}/{count}] 生成图片...")
            image = self.image_gen.generate(
                prompt=image_prompt,
                style=self.style,
                size=self.image_size
            )
            
            if image:
                filename = f"image_{i+1:02d}.png"
                filepath = os.path.join(sub_dir, filename)
                image.save(filepath)
                results["images"].append(filepath)
                print(f"    ✓ 已保存: {filepath}")
            else:
                print(f"    ✗ 生成失败")
        
        # 生成语录
        print(f"\n正在生成{quote_style}风格语录...")
        quotes = self.quote_gen.generate_quotes(
            keywords=keywords,
            count=count,
            style=quote_style
        )
        results["quotes"] = quotes
        
        # 保存语录到文件
        quote_file = os.path.join(sub_dir, "quotes.txt")
        with open(quote_file, "w", encoding="utf-8") as f:
            f.write(f"# 性格关键词: {keywords}\n")
            f.write(f"# 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 语录风格: {quote_style}\n\n")
            for i, quote in enumerate(quotes, 1):
                f.write(f"[{i}] {quote}\n\n")
        
        print(f"  ✓ 语录已保存到: {quote_file}")
        
        # 创建配对文件（方便后续使用）
        pairing_file = os.path.join(sub_dir, "pairing.json")
        import json
        pairing = []
        for i in range(min(count, len(results["images"]), len(quotes))):
            pairing.append({
                "image": f"image_{i+1:02d}.png",
                "quote": quotes[i]
            })
        with open(pairing_file, "w", encoding="utf-8") as f:
            json.dump(pairing, f, ensure_ascii=False, indent=2)
        
        print(f"  ✓ 配对文件已保存: {pairing_file}")
        
        # 打印语录预览
        print("\n" + "="*50)
        print("语录预览:")
        print("="*50)
        for i, quote in enumerate(quotes, 1):
            print(f"\n[{i}] {quote}")
        
        print(f"\n{'='*50}")
        print(f"生成完成！")
        print(f"输出目录: {sub_dir}")
        print(f"{'='*50}\n")
        
        return results


def load_config_from_env():
    """从环境变量加载配置"""
    load_dotenv()
    
    return {
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        "openai_base_url": os.getenv("OPENAI_BASE_URL"),
        "sd_webui_url": os.getenv("SD_WEBUI_URL"),
        "generator_type": os.getenv("GENERATOR_TYPE", "openai"),
        "style": os.getenv("IMAGE_STYLE", "anime"),
        "image_size": os.getenv("IMAGE_SIZE", "512x768"),
        "output_dir": os.getenv("OUTPUT_DIR", "output")
    }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AI 美女图片+情感语录自动生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --keywords "温柔,独立,自信" --count 5
  python main.py --keywords "活泼,阳光" --count 3 --style anime --quote-style romantic
  python main.py --keywords "优雅,知性" --count 4 --generator sd
        """
    )
    
    parser.add_argument(
        "--keywords",
        type=str,
        required=True,
        help="性格关键词，用逗号分隔，如: 温柔,独立,自信"
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="生成数量 (默认: 5)"
    )
    
    parser.add_argument(
        "--style",
        type=str,
        choices=["anime", "realistic", "semi_realistic"],
        default=None,
        help="图片风格 (默认: 从.env或anime)"
    )
    
    parser.add_argument(
        "--quote-style",
        type=str,
        choices=["emotional", "inspirational", "romantic", "philosophical"],
        default="emotional",
        help="语录风格 (默认: emotional)"
    )
    
    parser.add_argument(
        "--generator",
        type=str,
        choices=["openai", "sd"],
        default=None,
        help="图片生成器 (默认: openai)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="输出目录 (默认: output)"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config_from_env()
    
    # 命令行参数覆盖配置文件
    if args.style:
        config["style"] = args.style
    if args.generator:
        config["generator_type"] = args.generator
    if args.output_dir:
        config["output_dir"] = args.output_dir
    
    # 设置默认值
    config.setdefault("style", "anime")
    config.setdefault("generator_type", "openai")
    config.setdefault("output_dir", "output")
    
    try:
        # 创建生成器并执行
        ai = AIGenerator(config)
        results = ai.generate(
            keywords=args.keywords,
            count=args.count,
            quote_style=args.quote_style
        )
        
        print(f"\n🎉 全部完成！输出目录: {results['output_dir']}")
        
    except ValueError as e:
        print(f"\n❌ 配置错误: {e}")
        print("请检查 .env 文件是否正确配置")
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()