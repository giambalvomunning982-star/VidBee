"""
AI 视频自动化处理监控脚本

功能：
1. 监控 E:\my_project\downloads 文件夹
2. 当有新视频文件下载完成时自动触发
3. 对视频进行分析，提取标题/描述信息
4. 生成配套的美女图片和情感语录
5. 输出到独立的处理结果目录

用法：
    python monitor_and_process.py
    python monitor_and_process.py --watch-dir "E:\my_project\downloads"
    python monitor_and_process.py --style anime --count 3
"""

import os
import sys
import time
import json
import hashlib
import argparse
import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 导入本地模块
from image_generator import (
    OpenAIGenerator,
    SDGenerator,
    create_image_prompt,
    generate_negative_prompt
)
from quote_generator import QuoteGenerator


# 支持的视频文件格式
VIDEO_EXTENSIONS = {
    '.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.3gp'
}

# 冷却时间（秒）- 等待文件写入完成
COOLDOWN_SECONDS = 3

# 监控间隔（秒）
POLL_INTERVAL = 1.0


class VideoAnalyzer:
    """视频分析器 - 使用 AI 分析视频内容"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com"
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        except ImportError:
            self.client = None
    
    def analyze_video_metadata(self, video_path: str) -> dict:
        """
        分析视频元数据，提取有用信息
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            包含视频信息的字典
        """
        path = Path(video_path)
        filename = path.stem  # 不带扩展名的文件名
        
        # 尝试从文件名提取关键词
        keywords = self._extract_keywords_from_filename(filename)
        
        # 如果有 ffmpeg，可以尝试获取视频时长等信息
        video_info = self._get_video_info(video_path)
        
        return {
            "filename": filename,
            "original_name": path.name,
            "extension": path.suffix,
            "keywords": keywords,
            "file_size": path.stat().st_size,
            "created": datetime.datetime.fromtimestamp(path.stat().st_ctime).isoformat(),
            "modified": datetime.datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            **video_info
        }
    
    def _extract_keywords_from_filename(self, filename: str) -> str:
        """从文件名提取关键词"""
        # 移除常见后缀
        clean_name = filename.replace('_', ' ').replace('-', ' ')
        
        # 常见视频平台后缀移除
        suffixes = [
            'youtube', 'tiktok', 'instagram', 'bilibili', 'douyin',
            'twitter', 'weibo', 'facebook', 'twitch', 'reddit',
            'download', 'vidbee', 'mp4', 'mkv'
        ]
        for suffix in suffixes:
            clean_name = clean_name.replace(suffix, '')
        
        # 清理多余空格
        keywords = ' '.join(clean_name.split())
        
        return keywords if keywords else "beautiful_woman"
    
    def _get_video_info(self, video_path: str) -> dict:
        """获取视频基本信息"""
        info = {}
        try:
            import subprocess
            # 使用 ffprobe 获取视频信息
            result = subprocess.run(
                [
                    'ffprobe', '-v', 'quiet',
                    '-print_format', 'json',
                    '-show_format', '-show_streams',
                    video_path
                ],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        info['duration'] = data.get('format', {}).get('duration', 'N/A')
                        info['resolution'] = f"{stream.get('width', 'N/A')}x{stream.get('height', 'N/A')}"
                        break
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass
        
        return info
    
    def generate_ai_keywords(self, filename: str) -> str:
        """
        使用 AI 生成性格关键词
        
        Args:
            filename: 视频文件名（或标题）
            
        Returns:
            性格关键词字符串
        """
        if not self.client:
            return "温柔,独立,自信"
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个内容分析专家。根据视频标题或描述，推断可能适合的人物性格关键词。只返回3-5个中文关键词，用逗号分隔。"
                    },
                    {
                        "role": "user",
                        "content": f"视频标题/文件名: {filename}\n\n请推断适合的人物性格关键词："
                    }
                ],
                temperature=0.7,
                max_tokens=50
            )
            
            keywords = response.choices[0].message.content.strip()
            # 清理可能的多余内容
            keywords = keywords.split('\n')[0].strip()
            return keywords if keywords else "温柔,独立,自信"
            
        except Exception as e:
            print(f"  ⚠ AI 关键词生成失败: {e}")
            return "温柔,独立,自信"


class VideoMonitor:
    """视频文件夹监控器"""
    
    def __init__(
        self,
        watch_dir: str,
        output_dir: str = "output",
        style: str = "anime",
        count: int = 3,
        quote_style: str = "emotional",
        generator_type: str = "openai"
    ):
        self.watch_dir = Path(watch_dir)
        self.output_dir = Path(output_dir)
        self.style = style
        self.count = count
        self.quote_style = quote_style
        self.generator_type = generator_type
        
        # 已处理文件的哈希记录
        self.processed_files = set()
        
        # 加载配置
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com")
        
        # 初始化组件
        self.analyzer = VideoAnalyzer(self.api_key, self.base_url)
        self.image_gen = self._init_image_generator()
        self.quote_gen = QuoteGenerator(self.api_key, self.base_url)
        
        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)
        
        # 加载已处理记录
        self._load_processed_records()
    
    def _init_image_generator(self):
        """初始化图片生成器"""
        if self.generator_type == "openai":
            return OpenAIGenerator(self.api_key, self.base_url)
        elif self.generator_type == "sd":
            sd_url = os.getenv("SD_WEBUI_URL", "http://127.0.0.1:7860")
            return SDGenerator(sd_url)
        else:
            return OpenAIGenerator(self.api_key, self.base_url)
    
    def _load_processed_records(self):
        """加载已处理文件记录"""
        record_file = self.output_dir / "processed_records.json"
        if record_file.exists():
            try:
                with open(record_file, 'r', encoding='utf-8') as f:
                    self.processed_files = set(json.load(f))
                print(f"📋 已加载 {len(self.processed_files)} 条已处理记录")
            except Exception:
                self.processed_files = set()
    
    def _save_processed_record(self, file_hash: str):
        """保存已处理记录"""
        record_file = self.output_dir / "processed_records.json"
        self.processed_files.add(file_hash)
        # 每处理10个文件保存一次
        if len(self.processed_files) % 10 == 0:
            try:
                with open(record_file, 'w', encoding='utf-8') as f:
                    json.dump(list(self.processed_files), f, indent=2)
            except Exception as e:
                print(f"  ⚠ 保存记录失败: {e}")
    
    def _get_file_hash(self, file_path: Path) -> str:
        """获取文件哈希（用于检测文件是否变化）"""
        try:
            # 使用修改时间和大小作为快速标识
            stat = file_path.stat()
            content = f"{stat.st_size}:{stat.st_mtime}"
            return hashlib.md5(content.encode()).hexdigest()
        except Exception:
            return ""
    
    def _is_video_file(self, file_path: Path) -> bool:
        """检查是否为视频文件"""
        return file_path.suffix.lower() in VIDEO_EXTENSIONS
    
    def _is_file_ready(self, file_path: Path) -> bool:
        """检查文件是否写入完成"""
        try:
            # 尝试以独占模式打开文件，如果失败说明正在被写入
            with open(file_path, 'r') as f:
                pass
            return True
        except (PermissionError, IOError):
            return False
    
    def process_video(self, video_path: Path) -> bool:
        """
        处理单个视频文件
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            是否处理成功
        """
        print(f"\n{'='*60}")
        print(f"🎬 检测到新视频: {video_path.name}")
        print(f"{'='*60}")
        
        # 分析视频
        print("\n📊 分析视频信息...")
        video_info = self.analyzer.analyze_video_metadata(str(video_path))
        print(f"   文件名: {video_info['filename']}")
        print(f"   文件大小: {self._format_size(video_info['file_size'])}")
        
        # 生成 AI 关键词
        print("\n🤖 生成性格关键词...")
        keywords = self.analyzer.generate_ai_keywords(video_info['filename'])
        print(f"   关键词: {keywords}")
        
        # 创建输出目录
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        keyword_short = keywords.replace(",", "_")[:20]
        sub_dir = self.output_dir / f"{keyword_short}_{timestamp}"
        os.makedirs(sub_dir, exist_ok=True)
        
        print(f"\n📁 输出目录: {sub_dir}")
        
        # 生成图片
        print("\n🎨 生成配套图片...")
        image_prompt = create_image_prompt(keywords, self.style)
        print(f"   提示词: {image_prompt[:80]}...")
        
        generated_images = []
        for i in range(self.count):
            print(f"   [{i+1}/{self.count}] 生成图片...")
            image = self.image_gen.generate(
                prompt=image_prompt,
                style=self.style,
                size=os.getenv("IMAGE_SIZE", "512x768")
            )
            
            if image:
                filename = f"image_{i+1:02d}.png"
                filepath = sub_dir / filename
                image.save(filepath)
                generated_images.append(str(filepath))
                print(f"      ✓ 已保存: {filename}")
            else:
                print(f"      ✗ 生成失败")
        
        # 生成语录
        print(f"\n💬 生成{self.quote_style}风格语录...")
        try:
            quotes = self.quote_gen.generate_quotes(
                keywords=keywords,
                count=self.count,
                style=self.quote_style
            )
        except Exception as e:
            print(f"  ⚠ 语录生成失败: {e}")
            quotes = []
        
        # 保存语录
        if quotes:
            quote_file = sub_dir / "quotes.txt"
            with open(quote_file, "w", encoding="utf-8") as f:
                f.write(f"# 视频来源: {video_info['original_name']}\n")
                f.write(f"# 性格关键词: {keywords}\n")
                f.write(f"# 生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 语录风格: {self.quote_style}\n\n")
                for i, quote in enumerate(quotes, 1):
                    f.write(f"[{i}] {quote}\n\n")
            print(f"  ✓ 语录已保存: quotes.txt")
        
        # 保存配对文件
        pairing_file = sub_dir / "pairing.json"
        pairing = []
        for i in range(min(len(generated_images), len(quotes))):
            pairing.append({
                "image": f"image_{i+1:02d}.png",
                "quote": quotes[i] if i < len(quotes) else ""
            })
        with open(pairing_file, "w", encoding="utf-8") as f:
            json.dump(pairing, f, ensure_ascii=False, indent=2)
        print(f"  ✓ 配对文件已保存: pairing.json")
        
        # 保存视频信息
        info_file = sub_dir / "video_info.json"
        with open(info_file, "w", encoding="utf-8") as f:
            json.dump(video_info, f, ensure_ascii=False, indent=2)
        
        # 记录已处理
        file_hash = self._get_file_hash(video_path)
        if file_hash:
            self._save_processed_record(file_hash)
        
        print(f"\n{'='*60}")
        print(f"✅ 处理完成！")
        print(f"   输出目录: {sub_dir}")
        print(f"   图片数量: {len(generated_images)}")
        print(f"   语录数量: {len(quotes)}")
        print(f"{'='*60}")
        
        return True
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
    
    def monitor(self):
        """启动监控"""
        print(f"\n{'='*60}")
        print("👁️  VidBee 视频自动化处理监控")
        print(f"{'='*60}")
        print(f"📂 监控目录: {self.watch_dir}")
        print(f"📁 输出目录: {self.output_dir}")
        print(f"🎨 图片风格: {self.style}")
        print(f"🔢 生成数量: {self.count}")
        print(f"💬 语录风格: {self.quote_style}")
        print(f"⚙️  生成器: {self.generator_type}")
        print(f"\n⏳ 等待新视频... (按 Ctrl+C 停止)")
        print(f"{'='*60}\n")
        
        # 确保监控目录存在
        if not self.watch_dir.exists():
            print(f"❌ 监控目录不存在: {self.watch_dir}")
            print("   请创建目录或修改 --watch-dir 参数")
            sys.exit(1)
        
        last_scan_size = 0
        
        try:
            while True:
                # 扫描目录
                current_files = set()
                new_files = []
                
                for file_path in self.watch_dir.iterdir():
                    if file_path.is_file() and self._is_video_file(file_path):
                        file_hash = self._get_file_hash(file_path)
                        current_files.add(file_hash)
                        
                        # 检查是否为新文件且写入完成
                        if file_hash not in self.processed_files and self._is_file_ready(file_path):
                            new_files.append(file_path)
                
                # 检测新文件
                if new_files:
                    for new_file in sorted(new_files):
                        time.sleep(COOLDOWN_SECONDS)  # 等待文件写入完成
                        self.process_video(new_file)
                else:
                    # 静默等待
                    time.sleep(POLL_INTERVAL)
                    
        except KeyboardInterrupt:
            print(f"\n\n{'='*60}")
            print("🛑 监控已停止")
            print(f"{'='*60}")
            # 保存最终记录
            self._save_processed_record("")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="VidBee 视频自动化处理监控",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python monitor_and_process.py
  python monitor_and_process.py --watch-dir "D:\\videos" --style anime --count 5
  python monitor_and_process.py --style realistic --quote-style romantic --generator sd
        """
    )
    
    parser.add_argument(
        "--watch-dir",
        type=str,
        default=r"E:\my_project\downloads",
        help="监控目录 (默认: E:\\my_project\\downloads)"
    )
    
    parser.add_argument(
        "--output-dir",
        type=str,
        default="output",
        help="输出目录 (默认: output)"
    )
    
    parser.add_argument(
        "--style",
        type=str,
        choices=["anime", "realistic", "semi_realistic"],
        default=None,
        help="图片风格 (默认: 从.env或anime)"
    )
    
    parser.add_argument(
        "--count",
        type=int,
        default=3,
        help="生成数量 (默认: 3)"
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
    
    args = parser.parse_args()
    
    # 加载配置
    load_dotenv()
    
    config = {
        "style": args.style or os.getenv("IMAGE_STYLE", "anime"),
        "count": args.count,
        "quote_style": args.quote_style,
        "generator_type": args.generator or os.getenv("GENERATOR_TYPE", "openai"),
        "watch_dir": args.watch_dir,
        "output_dir": args.output_dir
    }
    
    try:
        monitor = VideoMonitor(
            watch_dir=config["watch_dir"],
            output_dir=config["output_dir"],
            style=config["style"],
            count=config["count"],
            quote_style=config["quote_style"],
            generator_type=config["generator_type"]
        )
        monitor.monitor()
        
    except Exception as e:
        print(f"\n❌ 监控启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()