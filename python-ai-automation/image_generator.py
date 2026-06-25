"""
AI Image Generator for VidBee Automation

Supports OpenAI DALL-E and Stable Diffusion WebUI.
"""

import os
import base64
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class ImageGenerator:
    """Generate AI images using OpenAI DALL-E or Stable Diffusion."""

    STYLES = {
        "anime": {
            "suffix": ", anime style, beautiful girl, vibrant colors, detailed anime art",
            "negative_prompt": "realistic, photorealistic, 3d, render, western cartoon",
        },
        "realistic": {
            "suffix": ", photorealistic, realistic photo, high quality photography",
            "negative_prompt": "anime, cartoon, drawing, painting, illustration, 3d, render",
        },
        "semi_realistic": {
            "suffix": ", semi-realistic art style, detailed illustration, soft lighting",
            "negative_prompt": "anime, overly cartoonish, photorealistic, 3d render",
        },
    }

    def __init__(
        self,
        style: str = "anime",
        generator_type: str = "openai",
        size: str = "512x512",
        output_dir: str = "output/images",
    ):
        self.style = style
        self.generator_type = generator_type
        self.size = size
        self.output_path = Path(output_dir)
        self.output_path.mkdir(parents=True, exist_ok=True)

        self.openai_image_model = os.getenv("OPENAI_IMAGE_MODEL", "dall-e-3")
        self.agnes_image_model = os.getenv("AGNES_IMAGE_MODEL") or self.openai_image_model

        if generator_type == "openai":
            api_key = os.getenv("OPENAI_API_KEY")
            base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.client = OpenAI(api_key=api_key, base_url=base_url)
        elif generator_type == "agnes":
            self.agnes_api_key = os.getenv("AGNES_API_KEY")
            self.agnes_image_url = os.getenv("AGNES_IMAGE_API_URL")
            agnes_base_url = os.getenv("AGNES_OPENAI_BASE_URL") or os.getenv("AGNES_API_BASE_URL")
            self.client = (
                OpenAI(api_key=self.agnes_api_key, base_url=agnes_base_url)
                if agnes_base_url
                else None
            )
        elif generator_type == "sd":
            self.sd_url = os.getenv("SD_WEBUI_URL", "http://127.0.0.1:7860")

    def generate_prompts(self, keywords: list, count: int = 3) -> list:
        """Generate image prompts from keywords."""
        style_config = self.STYLES.get(self.style, self.STYLES["anime"])

        prompts = []
        scenes = [
            "a peaceful garden at sunset",
            "standing by a window on a rainy day",
            "walking through a field of flowers",
            "reading a book in a cozy cafe",
            "watching the stars on a clear night",
            "sitting on a beach at dawn",
            "dancing in the rain",
            "playing with pets in a park",
            "cooking in a warm kitchen",
            "meditating in a serene forest",
        ]

        for i in range(count):
            keyword = keywords[i % len(keywords)] if keywords else "beautiful"
            scene = scenes[i % len(scenes)]
            prompt = f"a beautiful young woman, {keyword}, {scene}{style_config['suffix']}"
            prompts.append(prompt)

        return prompts

    def generate_images(self, prompts: list) -> list:
        """Generate images from prompts."""
        if self.generator_type == "openai":
            return self._generate_with_openai(prompts)
        elif self.generator_type == "agnes":
            return self._generate_with_agnes(prompts)
        elif self.generator_type == "sd":
            return self._generate_with_sd(prompts)
        else:
            raise ValueError(f"Unknown generator type: {self.generator_type}")

    def _generate_with_openai(self, prompts: list) -> list:
        """Generate images using OpenAI DALL-E."""
        image_paths = []

        for i, prompt in enumerate(prompts):
            try:
                print(f"   Generating image {i + 1}/{len(prompts)}...")
                response = self.client.images.generate(
                    model=self.openai_image_model,
                    prompt=prompt,
                    size=self.size,
                    n=1,
                    response_format="b64_json",
                )

                image_data = response.data[0].b64_json
                filename = f"image_{i + 1:02d}.png"
                filepath = self.output_path / filename

                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(image_data))

                image_paths.append(filepath)
                print(f"   Saved: {filepath.name}")

            except Exception as e:
                print(f"   Error generating image {i + 1}: {e}")

        return image_paths

    def _generate_with_agnes(self, prompts: list) -> list:
        """Generate images using Agnes image API or an OpenAI-compatible Agnes endpoint."""
        if self.agnes_image_url:
            return self._generate_with_agnes_rest(prompts)

        if not self.client:
            raise ValueError("AGNES_IMAGE_API_URL or AGNES_OPENAI_BASE_URL is required for Agnes images.")

        return self._generate_with_openai_compatible(
            prompts=prompts,
            model=self.agnes_image_model,
        )

    def _generate_with_openai_compatible(self, prompts: list, model: str) -> list:
        """Generate images through an OpenAI-compatible images API."""
        image_paths = []

        for i, prompt in enumerate(prompts):
            try:
                print(f"   Generating image {i + 1}/{len(prompts)}...")
                response = self.client.images.generate(
                    model=model,
                    prompt=prompt,
                    size=self.size,
                    n=1,
                    response_format="b64_json",
                )

                image_data = response.data[0].b64_json
                filename = f"image_{i + 1:02d}.png"
                filepath = self.output_path / filename

                with open(filepath, "wb") as f:
                    f.write(base64.b64decode(image_data))

                image_paths.append(filepath)
                print(f"   Saved: {filepath.name}")

            except Exception as e:
                print(f"   Error generating image {i + 1}: {e}")

        return image_paths

    def _generate_with_agnes_rest(self, prompts: list) -> list:
        """Generate images using a configured Agnes REST image endpoint."""
        image_paths = []
        headers = {"Content-Type": "application/json"}
        if self.agnes_api_key:
            headers["Authorization"] = f"Bearer {self.agnes_api_key}"

        for i, prompt in enumerate(prompts):
            try:
                print(f"   Generating image {i + 1}/{len(prompts)}...")
                payload = {
                    "model": self.agnes_image_model,
                    "prompt": prompt,
                    "size": self.size,
                    "n": 1,
                    "response_format": "b64_json",
                }
                response = requests.post(
                    self.agnes_image_url,
                    headers=headers,
                    json=payload,
                    timeout=120,
                )
                response.raise_for_status()
                image_data = self._extract_image_data(response.json())

                filename = f"image_{i + 1:02d}.png"
                filepath = self.output_path / filename
                with open(filepath, "wb") as f:
                    f.write(image_data)

                image_paths.append(filepath)
                print(f"   Saved: {filepath.name}")
                time.sleep(1)

            except Exception as e:
                print(f"   Error generating image {i + 1}: {e}")

        return image_paths

    def _extract_image_data(self, data: dict) -> bytes:
        """Extract image bytes from common API response shapes."""
        candidates = []
        if isinstance(data.get("data"), list):
            candidates.extend(item for item in data["data"] if isinstance(item, dict))
        if isinstance(data.get("output"), list):
            candidates.extend(item for item in data["output"] if isinstance(item, dict))
        candidates.append(data)

        for item in candidates:
            b64_json = item.get("b64_json") or item.get("image_base64") or item.get("image")
            if isinstance(b64_json, str):
                clean_value = b64_json.removeprefix("data:image/png;base64,")
                return base64.b64decode(clean_value)

            image_url = item.get("url") or item.get("image_url") or item.get("output_url")
            if isinstance(image_url, str) and image_url.startswith(("http://", "https://")):
                response = requests.get(image_url, timeout=120)
                response.raise_for_status()
                return response.content

        raise ValueError("Agnes image response did not include image data.")

    def _generate_with_sd(self, prompts: list) -> list:
        """Generate images using Stable Diffusion WebUI API."""
        image_paths = []
        style_config = self.STYLES.get(self.style, self.STYLES["anime"])

        for i, prompt in enumerate(prompts):
            try:
                print(f"   Generating image {i + 1}/{len(prompts)}...")

                payload = {
                    "prompt": f"{prompt}, masterpiece, best quality, highres",
                    "negative_prompt": f"{style_config['negative_prompt']}, lowres, bad anatomy",
                    "steps": 20,
                    "cfg_scale": 7,
                    "width": int(self.size.split("x")[0]),
                    "height": int(self.size.split("x")[1]),
                }

                response = requests.post(
                    f"{self.sd_url}/sdapi/v1/txt2img",
                    json=payload,
                    timeout=120,
                )
                data = response.json()

                if "images" in data and data["images"]:
                    import base64
                    filename = f"image_{i + 1:02d}.png"
                    filepath = self.output_path / filename

                    with open(filepath, "wb") as f:
                        f.write(base64.b64decode(data["images"][0]))

                    image_paths.append(filepath)
                    print(f"   Saved: {filepath.name}")

                time.sleep(1)  # Rate limiting

            except Exception as e:
                print(f"   Error generating image {i + 1}: {e}")

        return image_paths
