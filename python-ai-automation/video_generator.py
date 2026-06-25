"""
Generic video generation API client for VidBee automation.

The script supports common async video generation APIs:
1. Submit a prompt to a configurable endpoint.
2. Poll a task/status endpoint when the API returns a task id.
3. Save a returned video URL or base64 payload to disk.

Configure it with VIDEO_* or AGNES_* variables in .env.
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_OUTPUT_DIR = "output/videos"
DEFAULT_AGNES_CHAT_COMPLETIONS_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
DEFAULT_POLL_INTERVAL_SECONDS = 5
DEFAULT_TIMEOUT_SECONDS = 600
REQUEST_TIMEOUT_SECONDS = 60
SUCCESS_STATUSES = {"completed", "complete", "done", "succeeded", "success"}
FAILED_STATUSES = {"failed", "failure", "error", "cancelled", "canceled"}
VIDEO_URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)


class VideoGenerationError(RuntimeError):
    """Raised when a video generation request cannot be completed."""


class VideoGenerator:
    """Submit video generation jobs and download the generated result."""

    def __init__(
        self,
        api_url: str,
        api_key: str | None,
        model: str | None = None,
        output_dir: str = DEFAULT_OUTPUT_DIR,
        status_url_template: str | None = None,
        api_format: str = "auto",
    ):
        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.output_path = Path(output_dir)
        self.status_url_template = status_url_template
        self.api_format = self._resolve_api_format(api_format)
        self.output_path.mkdir(parents=True, exist_ok=True)

    def generate(
        self,
        prompt: str,
        duration: int | None = None,
        aspect_ratio: str | None = None,
        size: str | None = None,
        payload_overrides: dict[str, Any] | None = None,
        poll_interval: int = DEFAULT_POLL_INTERVAL_SECONDS,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> Path:
        """Generate a video from a text prompt and save it locally."""
        payload = self._build_payload(
            prompt=prompt,
            duration=duration,
            aspect_ratio=aspect_ratio,
            size=size,
            payload_overrides=payload_overrides,
        )

        print("Submitting video generation request...")
        response_data = self._request("POST", self.api_url, json_payload=payload)
        result = self._resolve_result(response_data, poll_interval=poll_interval, timeout=timeout)

        filename = self._create_filename(prompt)
        filepath = self.output_path / filename
        self._save_video(result, filepath)
        return filepath

    def _build_payload(
        self,
        prompt: str,
        duration: int | None,
        aspect_ratio: str | None,
        size: str | None,
        payload_overrides: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if self.api_format == "chat_completions":
            return self._build_chat_completions_payload(
                prompt=prompt,
                duration=duration,
                aspect_ratio=aspect_ratio,
                size=size,
                payload_overrides=payload_overrides,
            )

        payload: dict[str, Any] = {"prompt": prompt}

        if self.model:
            payload["model"] = self.model
        if duration is not None:
            payload["duration"] = duration
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        if size:
            payload["size"] = size
        if payload_overrides:
            payload.update(payload_overrides)

        return payload

    def _build_chat_completions_payload(
        self,
        prompt: str,
        duration: int | None,
        aspect_ratio: str | None,
        size: str | None,
        payload_overrides: dict[str, Any] | None,
    ) -> dict[str, Any]:
        details = []
        if duration is not None:
            details.append(f"Duration: {duration} seconds.")
        if aspect_ratio:
            details.append(f"Aspect ratio: {aspect_ratio}.")
        if size:
            details.append(f"Size: {size}.")

        user_prompt = prompt
        if details:
            user_prompt = f"{prompt}\n\nVideo requirements:\n" + "\n".join(details)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a video generation model. Generate a video from the user prompt. "
                        "When the job is complete, return a downloadable video URL or JSON containing "
                        "video_url, download_url, output_url, result_url, task_id, or status_url."
                    ),
                },
                {"role": "user", "content": user_prompt},
            ],
        }
        if payload_overrides:
            payload.update(payload_overrides)

        return {key: value for key, value in payload.items() if value is not None}

    def _request(
        self,
        method: str,
        url: str,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                json=json_payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise VideoGenerationError(f"API request failed: {exc}") from exc

        try:
            return response.json()
        except ValueError as exc:
            raise VideoGenerationError("API returned a non-JSON response.") from exc

    def _resolve_result(
        self,
        response_data: dict[str, Any],
        poll_interval: int,
        timeout: int,
    ) -> dict[str, Any]:
        if self._extract_video_url(response_data) or self._extract_video_base64(response_data):
            return response_data

        if self.api_format == "chat_completions":
            raise VideoGenerationError(
                "Agnes chat completions response did not include a video URL or base64 video. "
                "Check that VIDEO_MODEL is a video-capable Agnes model and that the model returns a "
                "downloadable video result."
            )

        task_id = self._extract_task_id(response_data)
        if not task_id:
            raise VideoGenerationError("API response did not include a video result or task id.")

        status_url = self._build_status_url(task_id, response_data)
        print(f"Video task created: {task_id}")
        return self._poll_until_complete(status_url, poll_interval=poll_interval, timeout=timeout)

    def _build_status_url(self, task_id: str, response_data: dict[str, Any]) -> str:
        status_url = self._extract_status_url(response_data)
        if status_url:
            return status_url

        if self.status_url_template:
            return self.status_url_template.format(task_id=task_id, id=task_id)

        base_url = self.api_url.rstrip("/")
        return f"{base_url}/{task_id}"

    def _poll_until_complete(self, status_url: str, poll_interval: int, timeout: int) -> dict[str, Any]:
        deadline = time.monotonic() + timeout

        while time.monotonic() < deadline:
            response_data = self._request("GET", status_url)
            status = str(response_data.get("status") or response_data.get("state") or "").lower()

            if self._extract_video_url(response_data) or self._extract_video_base64(response_data):
                print("Video generation completed.")
                return response_data

            if status in FAILED_STATUSES:
                error = response_data.get("error") or response_data.get("message") or response_data
                raise VideoGenerationError(f"Video generation failed: {error}")

            if status:
                print(f"Current status: {status}")
            else:
                print("Waiting for video generation...")
            time.sleep(poll_interval)

        raise VideoGenerationError("Timed out while waiting for video generation.")

    def _save_video(self, response_data: dict[str, Any], filepath: Path) -> None:
        video_url = self._extract_video_url(response_data)
        if video_url:
            self._download_video(video_url, filepath)
            return

        video_base64 = self._extract_video_base64(response_data)
        if video_base64:
            filepath.write_bytes(base64.b64decode(video_base64))
            return

        raise VideoGenerationError("Completed response did not include a downloadable video.")

    def _download_video(self, url: str, filepath: Path) -> None:
        print(f"Downloading video: {url}")
        try:
            with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                response.raise_for_status()
                with filepath.open("wb") as output_file:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            output_file.write(chunk)
        except requests.RequestException as exc:
            raise VideoGenerationError(f"Video download failed: {exc}") from exc

    def _create_filename(self, prompt: str) -> str:
        safe_prompt = "".join(char if char.isalnum() else "_" for char in prompt.lower())
        safe_prompt = "_".join(part for part in safe_prompt.split("_") if part)[:48] or "video"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{safe_prompt}_{timestamp}.mp4"

    def _extract_task_id(self, data: dict[str, Any]) -> str | None:
        for key in ("id", "task_id", "job_id", "generation_id"):
            value = data.get(key)
            if value:
                return str(value)
        nested_data = data.get("data")
        if isinstance(nested_data, dict):
            return self._extract_task_id(nested_data)
        return None

    def _extract_status_url(self, data: dict[str, Any]) -> str | None:
        for key in ("status_url", "polling_url", "url"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value
        nested_data = data.get("data")
        if isinstance(nested_data, dict):
            return self._extract_status_url(nested_data)
        return None

    def _extract_video_url(self, data: dict[str, Any]) -> str | None:
        for key in ("video_url", "output_url", "download_url", "result_url"):
            value = data.get(key)
            if isinstance(value, str) and value.startswith(("http://", "https://")):
                return value

        output = data.get("output")
        if isinstance(output, str) and output.startswith(("http://", "https://")):
            return output
        if isinstance(output, list):
            for item in output:
                if isinstance(item, str) and item.startswith(("http://", "https://")):
                    return item
                if isinstance(item, dict):
                    nested_url = self._extract_video_url(item)
                    if nested_url:
                        return nested_url

        nested_data = data.get("data")
        if isinstance(nested_data, dict):
            return self._extract_video_url(nested_data)

        for text in self._iter_strings(data):
            for match in VIDEO_URL_PATTERN.findall(text):
                clean_url = match.rstrip(".,)]}")
                if self._looks_like_video_url(clean_url):
                    return clean_url
        return None

    def _extract_video_base64(self, data: dict[str, Any]) -> str | None:
        for key in ("video", "video_base64", "b64_json"):
            value = data.get(key)
            if isinstance(value, str):
                return value.removeprefix("data:video/mp4;base64,")

        nested_data = data.get("data")
        if isinstance(nested_data, dict):
            return self._extract_video_base64(nested_data)
        return None

    def _iter_strings(self, value: Any):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for item in value.values():
                yield from self._iter_strings(item)
        elif isinstance(value, list):
            for item in value:
                yield from self._iter_strings(item)

    def _looks_like_video_url(self, url: str) -> bool:
        lower_url = url.lower()
        video_markers = (".mp4", ".mov", ".webm", ".mkv", "video", "download")
        return any(marker in lower_url for marker in video_markers)

    def _resolve_api_format(self, api_format: str) -> str:
        if api_format != "auto":
            return api_format

        if self.api_url.endswith("/chat/completions"):
            return "chat_completions"

        return "generations"


def parse_payload_json(value: str | None) -> dict[str, Any] | None:
    """Parse optional JSON payload overrides from the CLI."""
    if not value:
        return None

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise argparse.ArgumentTypeError(f"Invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise argparse.ArgumentTypeError("--payload-json must be a JSON object.")
    return parsed


def default_video_api_url() -> str | None:
    agnes_base_url = os.getenv("AGNES_API_BASE_URL")
    if os.getenv("VIDEO_API_URL"):
        return os.getenv("VIDEO_API_URL")
    if os.getenv("AGNES_VIDEO_API_URL"):
        return os.getenv("AGNES_VIDEO_API_URL")
    if agnes_base_url:
        return f"{agnes_base_url.rstrip('/')}/chat/completions"
    return DEFAULT_AGNES_CHAT_COMPLETIONS_URL


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate a video with a configurable API.")
    parser.add_argument("--prompt", required=True, help="Text prompt for the video.")
    parser.add_argument(
        "--api-url",
        default=default_video_api_url(),
        help="Video generation API URL.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("VIDEO_API_KEY") or os.getenv("AGNES_API_KEY") or os.getenv("OPENAI_API_KEY"),
    )
    parser.add_argument(
        "--model",
        default=os.getenv("VIDEO_MODEL") or os.getenv("AGNES_VIDEO_MODEL"),
        help="Video generation model name.",
    )
    parser.add_argument("--duration", type=int, default=None, help="Video duration in seconds.")
    parser.add_argument("--aspect-ratio", default=None, help="Aspect ratio, for example 16:9 or 9:16.")
    parser.add_argument("--size", default=None, help="Video size, for example 1280x720.")
    parser.add_argument("--output-dir", default=os.getenv("VIDEO_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--status-url-template",
        default=os.getenv("VIDEO_STATUS_URL_TEMPLATE") or os.getenv("AGNES_VIDEO_STATUS_URL_TEMPLATE"),
        help="Polling URL template, for example https://api.example.com/videos/{task_id}.",
    )
    parser.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL_SECONDS)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument(
        "--api-format",
        choices=["auto", "generations", "chat_completions"],
        default=os.getenv("VIDEO_API_FORMAT") or os.getenv("AGNES_VIDEO_API_FORMAT") or "auto",
        help="Request payload format. Use chat_completions for Agnes OpenAI-compatible chat endpoints.",
    )
    parser.add_argument(
        "--payload-json",
        type=parse_payload_json,
        default=None,
        help='Extra JSON fields merged into the request payload, for example {"seed":123}.',
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.api_url:
        print("Error: VIDEO_API_URL, AGNES_VIDEO_API_URL, or --api-url is required.")
        sys.exit(1)

    generator = VideoGenerator(
        api_url=args.api_url,
        api_key=args.api_key,
        model=args.model,
        output_dir=args.output_dir,
        status_url_template=args.status_url_template,
        api_format=args.api_format,
    )

    try:
        video_path = generator.generate(
            prompt=args.prompt,
            duration=args.duration,
            aspect_ratio=args.aspect_ratio,
            size=args.size,
            payload_overrides=args.payload_json,
            poll_interval=args.poll_interval,
            timeout=args.timeout,
        )
    except VideoGenerationError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    print(f"Video saved to: {video_path}")


if __name__ == "__main__":
    main()
