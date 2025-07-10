import json
import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class PhotoPrismConfig:
    url: str = ""
    username: str = ""
    password: str = ""
    
    def is_complete(self) -> bool:
        return all([self.url, self.username, self.password])


@dataclass
class LycheeConfig:
    url: str = ""
    username: str = ""
    password: str = ""
    
    def is_complete(self) -> bool:
        return all([self.url, self.username, self.password])


@dataclass
class AppConfig:
    photoprism: PhotoPrismConfig
    lychee: LycheeConfig
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AppConfig':
        return cls(
            photoprism=PhotoPrismConfig(
                url=data.get("photoprism_url", ""),
                username=data.get("photoprism_user", ""),
                password=data.get("photoprism_pass", "")
            ),
            lychee=LycheeConfig(
                url=data.get("lychee_url", ""),
                username=data.get("lychee_user", ""),
                password=data.get("lychee_pass", "")
            )
        )
    
    def to_dict(self) -> dict:
        return {
            "photoprism_url": self.photoprism.url,
            "photoprism_user": self.photoprism.username,
            "photoprism_pass": self.photoprism.password,
            "lychee_url": self.lychee.url,
            "lychee_user": self.lychee.username,
            "lychee_pass": self.lychee.password
        }


class ConfigManager:    
    def __init__(self, config_file: str = "photo_sync_config.json"):
        self.config_file = config_file
    
    def load_config(self) -> AppConfig:
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, "r") as f:
                    data = json.load(f)
                return AppConfig.from_dict(data)
        except Exception as e:
            print(f"Error loading config: {e}")
        
        # Return default config if loading fails
        return AppConfig(
            photoprism=PhotoPrismConfig(),
            lychee=LycheeConfig()
        )
    
    def save_config(self, config: AppConfig, silent: bool = False) -> bool:
        try:
            with open(self.config_file, "w") as f:
                json.dump(config.to_dict(), f, indent=2)
            return True
        except Exception as e:
            if not silent:
                print(f"Error saving config: {e}")
            return False