import os
import requests
from typing import Optional, Dict


class APICaller:
    @staticmethod
    def call_seedance(prompt: str, api_key: Optional[str] = None) -> Dict:
        key = api_key or os.getenv("SEEDANCE_API_KEY")
        if not key:
            raise ValueError("缺少 Seedance API Key")

        url = "https://api.seedance.com/v1/video/generate"
        headers = {"Authorization": f"Bearer {key}"}
        payload = {
            "prompt": prompt,
            "model": "seedance-2.0",
            "duration": 5,
        }

        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def check_seedance_status(task_id: str, api_key: Optional[str] = None) -> Dict:
        key = api_key or os.getenv("SEEDANCE_API_KEY")
        url = f"https://api.seedance.com/v1/video/status/{task_id}"
        headers = {"Authorization": f"Bearer {key}"}
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
