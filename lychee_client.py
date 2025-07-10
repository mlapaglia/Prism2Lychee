import requests
import urllib.parse
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config import LycheeConfig


@dataclass
class LycheeAlbum:
    id: str
    title: str
    owner: str
    indent: int = 0


class LycheeClient:    
    def __init__(self, config: LycheeConfig):
        self.config = config
        self.session: Optional[requests.Session] = None
    
    def connect(self) -> bool:
        if not self.config.is_complete():
            raise ValueError("Lychee configuration is incomplete")
        
        try:
            self.session = requests.Session()
            
            # Get CSRF token from home page
            home_response = self.session.get(self.config.url.rstrip('/'))
            
            xsrf_token = self._extract_xsrf_token()
            if not xsrf_token:
                raise Exception("Could not get CSRF token from Lychee")
            
            # Login
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "X-XSRF-TOKEN": xsrf_token
            }
            
            login_data = {
                "username": self.config.username,
                "password": self.config.password
            }
            
            response = self.session.post(
                f"{self.config.url.rstrip('/')}/api/v2/Auth::login",
                json=login_data,
                headers=headers
            )
            
            if response.status_code not in [200, 204]:
                error_msg = f"Login failed with status {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        if 'message' in error_data:
                            error_msg += f": {error_data['message']}"
                    except:
                        error_msg += f": {response.text[:200]}"
                raise Exception(error_msg)
            
            return True
            
        except Exception as e:
            raise Exception(f"Lychee connection error: {str(e)}")
    
    def get_albums(self) -> List[LycheeAlbum]:
        if not self.session:
            raise Exception("Not connected to Lychee")
        
        try:
            xsrf_token = self._extract_xsrf_token()
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            if xsrf_token:
                headers['X-XSRF-TOKEN'] = xsrf_token
            
            response = self.session.get(
                f"{self.config.url.rstrip('/')}/api/v2/Albums",
                headers=headers
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get albums: {response.status_code}")
            
            albums_data = response.json()
            return self._parse_albums(albums_data)
            
        except Exception as e:
            raise Exception(f"Error loading albums: {str(e)}")
    
    def upload_photo(self, photo_data: bytes, filename: str, album_id: str = "") -> bool:
        if not self.session:
            raise Exception("Not connected to Lychee")
        
        try:
            xsrf_token = self._extract_xsrf_token()
            content_type = self._get_content_type(filename)
            
            # Standard multipart upload
            files = {
                'file': (filename, photo_data, content_type)
            }
            
            data = {
                'file_name': filename,
                'uuid_name': '',
                'extension': '',
                'chunk_number': 1,
                'total_chunks': 1,
                'album_id': album_id,
            }
            
            headers = {
                'Accept': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            if xsrf_token:
                headers['X-XSRF-TOKEN'] = xsrf_token
            
            upload_url = f"{self.config.url.rstrip('/')}/api/v2/Photo"
            
            response = self.session.post(
                upload_url,
                files=files,
                data=data,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                return True
            
            # Try with multipart encoder if available
            try:
                from requests_toolbelt.multipart.encoder import MultipartEncoder
                
                multipart_data = MultipartEncoder(
                    fields={
                        'file': (filename, photo_data, content_type),
                        'file_name': filename,
                        'uuid_name': '',
                        'extension': '',
                        'chunk_number': '1',
                        'total_chunks': '1',
                        'album_id': album_id,
                    }
                )
                
                headers2 = {
                    'Content-Type': multipart_data.content_type,
                    'Accept': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
                
                if xsrf_token:
                    headers2['X-XSRF-TOKEN'] = xsrf_token
                
                response2 = self.session.post(
                    upload_url,
                    data=multipart_data,
                    headers=headers2
                )
                
                if response2.status_code in [200, 201]:
                    return True
                    
            except ImportError:
                pass
            
            # Handle upload failure
            error_msg = f"Upload failed with status {response.status_code}"
            try:
                error_data = response.json()
                if 'message' in error_data:
                    error_msg += f": {error_data['message']}"
                elif 'errors' in error_data:
                    error_msg += f": {error_data['errors']}"
            except:
                error_msg += f": {response.text[:200]}"
            
            raise Exception(error_msg)
            
        except Exception as e:
            raise Exception(f"Upload error: {str(e)}")
    
    def _extract_xsrf_token(self) -> Optional[str]:
        if not self.session:
            return None
        
        for cookie in self.session.cookies:
            if cookie.name == "XSRF-TOKEN":
                return urllib.parse.unquote(cookie.value or '')
        
        return None
    
    def _parse_albums(self, albums_data: Dict[str, Any]) -> List[LycheeAlbum]:
        albums = []
        
        def parse_albums_recursive(albums_list, indent=0):
            if isinstance(albums_list, dict):
                albums_list = (
                    albums_list.get('albums', []) or 
                    albums_list.get('data', [])
                )
                if not albums_list and 'smart_albums' in albums_list:
                    albums_list = (
                        albums_list.get('smart_albums', []) + 
                        albums_list.get('tag_albums', []) + 
                        albums_list.get('albums', [])
                    )
            
            for album in albums_list:
                if isinstance(album, dict):
                    album_id = album.get('id', '')
                    album_title = album.get('title', 'Untitled')
                    album_owner = album.get('owner_name', 'Unknown')
                    
                    albums.append(LycheeAlbum(
                        id=album_id,
                        title=album_title,
                        owner=album_owner,
                        indent=indent
                    ))
                    
                    # Parse nested albums
                    if 'albums' in album and album['albums']:
                        parse_albums_recursive(album['albums'], indent + 1)
        
        parse_albums_recursive(albums_data)
        return albums
    
    def _get_content_type(self, filename: str) -> str:
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        
        content_types = {
            'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
            'gif': 'image/gif', 'bmp': 'image/bmp', 'tiff': 'image/tiff',
            'webp': 'image/webp', 'heic': 'image/heic', 'heif': 'image/heif',
            'raw': 'image/raw', 'dng': 'image/dng', 'cr2': 'image/cr2',
            'nef': 'image/nef', 'arw': 'image/arw', 'orf': 'image/orf',
            'rw2': 'image/rw2', 'pef': 'image/pef', 'sr2': 'image/sr2',
            'raf': 'image/raf', 'mp4': 'video/mp4', 'mov': 'video/quicktime',
            'avi': 'video/avi', 'mkv': 'video/mkv'
        }
        
        return content_types.get(extension, 'application/octet-stream')