import requests
from typing import List, Dict, Any, Tuple, Optional, Mapping
from dataclasses import dataclass

from config import PhotoPrismConfig


@dataclass
class PhotoPrismTokens:
    access_token: str
    preview_token: str
    download_token: str


class PhotoPrismClient:
    
    def __init__(self, config: PhotoPrismConfig):
        self.config = config
        self.tokens: Optional[PhotoPrismTokens] = None
    
    def connect(self) -> bool:
        if not self.config.is_complete():
            raise ValueError("PhotoPrism configuration is incomplete")
        
        try:
            login_data = {
                "username": self.config.username,
                "password": self.config.password
            }
            
            response = requests.post(
                f"{self.config.url.rstrip('/')}/api/v1/session",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                raise Exception(f"Authentication failed: {response.status_code}")
            
            session_data = response.json()
            access_token = (
                session_data.get("access_token") or 
                session_data.get("session_id") or 
                session_data.get("id")
            )
            
            config_data = session_data.get("config", {})
            preview_token = config_data.get("previewToken", "")
            download_token = (
                session_data.get("download_token") or 
                session_data.get("downloadToken") or 
                config_data.get("downloadToken", "")
            )

            for header_name, header_value in response.headers.items():
                if "download" in header_name.lower() and "token" in header_name.lower():
                    download_token = header_value
                    break
            
            self.tokens = PhotoPrismTokens(
                access_token=access_token,
                preview_token=preview_token,
                download_token=download_token
            )
            
            return True
            
        except Exception as e:
            raise Exception(f"PhotoPrism connection error: {str(e)}")
    
    def search_photos(self, date: str, count: int = 100) -> List[Dict[str, Any]]:
        if not self.tokens:
            raise Exception("Not connected to PhotoPrism")
        
        try:
            params = {
                "count": count,
                "quality": 1,
                "q": f"taken:{date}",
                "merged": True
            }
            
            headers = {
                "Authorization": f"Bearer {self.tokens.access_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.config.url.rstrip('/')}/api/v1/photos",
                params=params,
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Photo search failed: {response.status_code}")
            
            return response.json()
            
        except Exception as e:
            raise Exception(f"Search error: {str(e)}")
    
    def get_thumbnail(self, photo: Dict[str, Any]) -> Optional[bytes]:
        if not self.tokens:
            raise Exception("Not connected to PhotoPrism")
        
        try:
            files = photo.get("Files", [])
            if not files:
                return None
            
            first_file = files[0]
            if first_file.get("Missing", False):
                return None
            
            file_hash = first_file.get("Hash", "")
            if not file_hash:
                return None
            
            thumb_url = f"{self.config.url.rstrip('/')}/api/v1/t/{file_hash}/{self.tokens.preview_token}/tile_500"
            response = requests.get(thumb_url)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'svg' in content_type.lower() or len(response.content) < 1000:
                    return None
                return response.content
            
            return None
            
        except Exception:
            return None
    
    def download_photo(self, photo: Dict[str, Any]) -> Tuple[bytes, str]:
        if not self.tokens:
            raise Exception("Not connected to PhotoPrism")
        
        try:
            photo_uid = photo.get('UID', '')
            if not photo_uid:
                raise Exception("No photo UID found")

            photo_details = self._get_photo_details(photo_uid)

            files = photo_details.get("Files", [])
            if not files:
                raise Exception("No files found in photo details")
            
            primary_file = self._get_primary_file(files)
            file_hash = primary_file.get("Hash", "")
            filename = primary_file.get("Name", "photo.jpg")
            
            if not file_hash:
                raise Exception("No file hash found")
            
            expected_size = primary_file.get('Size', 0)

            photo_data = self._try_download_with_token(file_hash, self.tokens.download_token, expected_size)
            if photo_data:
                return photo_data, filename
            raise Exception("All download methods failed")

        except Exception as e:
            raise Exception(f"Download error: {str(e)}")
    
    def _get_photo_details(self, photo_uid: str) -> Dict[str, Any]:
        assert self.tokens is not None
        photo_detail_url = f"{self.config.url.rstrip('/')}/api/v1/photos/{photo_uid}"
        headers = {
            "Authorization": f"Bearer {self.tokens.access_token}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(photo_detail_url, headers=headers)
        self._update_download_token_from_headers(response.headers)
        
        if response.status_code != 200:
            raise Exception(f"Failed to get photo details: {response.status_code}")
        
        return response.json()
    
    def _get_primary_file(self, files: List[Dict[str, Any]]) -> Dict[str, Any]:
        for file_info in files:
            if file_info.get("Primary", False):
                return file_info
        raise Exception("No primary file found")
    
    def _try_download_with_token(self, file_hash: str, token: str, expected_size: int) -> Optional[bytes]:
        download_url = f"{self.config.url.rstrip('/')}/api/v1/dl/{file_hash}?t={token}"
        response = requests.get(download_url)
        self._update_download_token_from_headers(response.headers)
        
        if self._is_valid_download_response(response, expected_size):
            return response.content
        
        return None
    
    def _is_valid_download_response(self, response: requests.Response, expected_size: int) -> bool:
        if response.status_code != 200:
            return False
        
        content_type = response.headers.get('content-type', '').lower()
        valid_types = ['image/', 'video/', 'application/octet-stream']
        
        if not any(t in content_type for t in valid_types) or 'svg' in content_type:
            return False
        
        actual_size = len(response.content)

        if expected_size > 0 and actual_size >= (expected_size * 0.8):
            return True
        
        return actual_size > 1000000  # At least 1MB
    
    def _update_download_token_from_headers(self, headers: Mapping[str, str]):
        if not self.tokens:
            return
        
        for header_name, header_value in headers.items():
            if "download" in header_name.lower() and "token" in header_name.lower():
                self.tokens = PhotoPrismTokens(
                    access_token=self.tokens.access_token,
                    preview_token=self.tokens.preview_token,
                    download_token=header_value
                )
                break