import requests
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from PIL import Image, ImageTk
import io
from datetime import datetime, timedelta
import threading
import json
import os
import urllib.parse
import uuid

class PhotoSyncApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PhotoPrism to Lychee Daily Photo Sync")
        self.root.geometry("1400x1000")
        
        # Configuration
        self.photoprism_url = ""
        self.photoprism_token = ""
        self.preview_token = ""
        self.download_token = ""
        self.lychee_url = ""
        self.lychee_session = None
        
        # Photo data
        self.current_photos = []
        self.selected_photo = None
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.thumbnail_cache = {}
        
        # Album data
        self.albums = []
        self.albums_dict = {}  # For quick lookup by ID
        
        self.setup_ui()
        self.load_config()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configuration frame
        config_frame = ttk.LabelFrame(main_frame, text="Configuration", padding="10")
        config_frame.grid(row=0, column=0, columnspan=2, sticky="we", pady=(0, 10))
        
        # PhotoPrism settings
        ttk.Label(config_frame, text="PhotoPrism URL:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.photoprism_url_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.photoprism_url_var, width=30).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(config_frame, text="PhotoPrism Username:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        self.photoprism_user_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.photoprism_user_var, width=20).grid(row=0, column=3, padx=(0, 10))
        
        ttk.Label(config_frame, text="PhotoPrism Password:").grid(row=1, column=0, sticky=tk.W, padx=(0, 5))
        self.photoprism_pass_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.photoprism_pass_var, show="*", width=20).grid(row=1, column=1, padx=(0, 10))
        
        # Lychee settings
        ttk.Label(config_frame, text="Lychee URL:").grid(row=1, column=2, sticky=tk.W, padx=(0, 5))
        self.lychee_url_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.lychee_url_var, width=30).grid(row=1, column=3)
        
        ttk.Label(config_frame, text="Lychee Username:").grid(row=2, column=0, sticky=tk.W, padx=(0, 5))
        self.lychee_user_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.lychee_user_var, width=20).grid(row=2, column=1, padx=(0, 10))
        
        ttk.Label(config_frame, text="Lychee Password:").grid(row=2, column=2, sticky=tk.W, padx=(0, 5))
        self.lychee_pass_var = tk.StringVar()
        ttk.Entry(config_frame, textvariable=self.lychee_pass_var, show="*", width=20).grid(row=2, column=3)
        
        # Connect buttons
        ttk.Button(config_frame, text="Connect PhotoPrism", command=self.connect_photoprism).grid(row=3, column=0, pady=10, padx=(0, 5))
        ttk.Button(config_frame, text="Connect Lychee", command=self.connect_lychee).grid(row=3, column=1, pady=10)
        
        # Date selection frame
        date_frame = ttk.LabelFrame(main_frame, text="Date Selection", padding="10")
        date_frame.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 10))
        
        ttk.Label(date_frame, text="Date:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.date_var = tk.StringVar(value=self.current_date)
        ttk.Entry(date_frame, textvariable=self.date_var, width=15).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Button(date_frame, text="Search Photos", command=self.search_photos).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(date_frame, text="Previous Day", command=self.previous_day).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(date_frame, text="Next Day", command=self.next_day).grid(row=0, column=4)
        
        # Photo selection frame
        photo_frame = ttk.LabelFrame(main_frame, text="Photo Selection", padding="10")
        photo_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        
        # Create scrollable frame for photos
        canvas = tk.Canvas(photo_frame, height=600)
        scrollbar = ttk.Scrollbar(photo_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.bind("<Configure>", self.on_canvas_resize)
        canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        canvas.bind("<Button-4>", self.on_mouse_wheel)
        canvas.bind("<Button-5>", self.on_mouse_wheel)
        
        canvas.focus_set()
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        self.canvas = canvas
        
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Action buttons
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=3, column=0, columnspan=2, sticky="we", pady=10)
        
        # Album selection dropdown
        ttk.Label(action_frame, text="Lychee Album:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.album_var = tk.StringVar()
        self.album_dropdown = ttk.Combobox(action_frame, textvariable=self.album_var, width=40, state="readonly")
        self.album_dropdown.grid(row=0, column=1, padx=(0, 10))
        
        # Initially populate with root album option
        self.album_dropdown['values'] = ["Root Album (No specific album)"]
        self.album_dropdown.set("Root Album (No specific album)")
        
        # Action buttons on second row
        ttk.Button(action_frame, text="Upload Selected to Lychee", command=self.upload_to_lychee).grid(row=1, column=0, pady=(5, 0), padx=(0, 10))
        ttk.Button(action_frame, text="Load Albums", command=self.load_lychee_albums).grid(row=1, column=1, pady=(5, 0), padx=(0, 10))
        ttk.Button(action_frame, text="Save Config", command=self.save_config).grid(row=1, column=2, pady=(5, 0))
        
        # Status label
        self.status_var = tk.StringVar(value="Ready. Please configure connections and search for photos.")
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Configure grid weights for proper resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        photo_frame.columnconfigure(0, weight=1)
        photo_frame.rowconfigure(0, weight=1)
        
    def calculate_grid_columns(self, canvas_width):
        thumbnail_width = 520  # 500px image + 20px padding
        min_columns = 1
        max_columns = 6
        
        if canvas_width < thumbnail_width:
            return min_columns
        
        return max(min_columns, min(max_columns, canvas_width // thumbnail_width))
    
    def on_mouse_wheel(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
    
    def on_canvas_resize(self, event):
        if hasattr(self, 'current_photos') and self.current_photos:
            self.root.after(100, lambda: self.update_photo_layout(event.width))
    
    def update_photo_layout(self, canvas_width):
        if not hasattr(self, 'current_photos') or not self.current_photos:
            return
        
        new_columns = self.calculate_grid_columns(canvas_width)
        
        if not hasattr(self, 'current_columns') or self.current_columns != new_columns:
            self.current_columns = new_columns
            self.display_photos()
    
    def connect_photoprism(self):
        self.photoprism_url = self.photoprism_url_var.get().rstrip('/')
        username = self.photoprism_user_var.get()
        password = self.photoprism_pass_var.get()
        
        if not all([self.photoprism_url, username, password]):
            messagebox.showerror("Error", "Please fill in all PhotoPrism connection details")
            return
        
        self.save_config_silent()
        
        try:
            login_data = {
                "username": username,
                "password": password
            }
            
            response = requests.post(
                f"{self.photoprism_url}/api/v1/session",
                json=login_data,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                session_data = response.json()
                self.photoprism_token = session_data.get("access_token") or session_data.get("session_id") or session_data.get("id")
                
                config = session_data.get("config", {})
                self.preview_token = config.get("previewToken", "")
                self.download_token = session_data.get("download_token") or session_data.get("downloadToken") or config.get("downloadToken", "")
                
                # Also check response headers for download token
                for header_name, header_value in response.headers.items():
                    if "download" in header_name.lower() and "token" in header_name.lower():
                        self.download_token = header_value
                        break
                
                self.status_var.set("Connected to PhotoPrism successfully!")
                messagebox.showinfo("Success", "Connected to PhotoPrism!")
            else:
                messagebox.showerror("Error", f"Failed to connect to PhotoPrism: {response.status_code}")
        except Exception as e:
            messagebox.showerror("Error", f"PhotoPrism connection error: {str(e)}")
    
    def connect_lychee(self):
        self.lychee_url = self.lychee_url_var.get().rstrip('/')
        username = self.lychee_user_var.get()
        password = self.lychee_pass_var.get()
        
        if not all([self.lychee_url, username, password]):
            messagebox.showerror("Error", "Please fill in all Lychee connection details")
            return
        
        self.save_config_silent()
        
        try:
            self.lychee_session = requests.Session()
            
            # Get CSRF token from home page
            home_response = self.lychee_session.get(f"{self.lychee_url}")
            
            xsrf_token = None
            for cookie in self.lychee_session.cookies:
                if cookie.name == "XSRF-TOKEN":
                    xsrf_token = urllib.parse.unquote(cookie.value or '')
                    break
            
            if not xsrf_token:
                messagebox.showerror("Error", "Could not get CSRF token from Lychee")
                return
            
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
                "X-XSRF-TOKEN": xsrf_token
            }
            
            login_data = {
                "username": username,
                "password": password
            }
            
            response = self.lychee_session.post(
                f"{self.lychee_url}/api/v2/Auth::login",
                json=login_data,
                headers=headers
            )
            
            if response.status_code in [200, 204]:
                self.status_var.set("Connected to Lychee successfully!")
                messagebox.showinfo("Success", "Connected to Lychee!")
            else:
                error_msg = f"Login failed with status {response.status_code}"
                if response.text:
                    try:
                        error_data = response.json()
                        if 'message' in error_data:
                            error_msg += f": {error_data['message']}"
                    except:
                        error_msg += f": {response.text[:200]}"
                
                messagebox.showerror("Error", error_msg)
                
        except Exception as e:
            messagebox.showerror("Error", f"Lychee connection error: {str(e)}")
    
    def save_config_silent(self):
        config = {
            "photoprism_url": self.photoprism_url_var.get(),
            "photoprism_user": self.photoprism_user_var.get(),
            "photoprism_pass": self.photoprism_pass_var.get(),
            "lychee_url": self.lychee_url_var.get(),
            "lychee_user": self.lychee_user_var.get(),
            "lychee_pass": self.lychee_pass_var.get()
        }
        
        try:
            with open("photo_sync_config.json", "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def search_photos(self):
        if not self.photoprism_token:
            messagebox.showerror("Error", "Please connect to PhotoPrism first")
            return
        
        search_date = self.date_var.get()
        
        try:
            params = {
                "count": 100,
                "quality": 1,
                "q": f"taken:{search_date}",
                "merged": True
            }
            
            headers = {
                "Authorization": f"Bearer {self.photoprism_token}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                f"{self.photoprism_url}/api/v1/photos",
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                self.current_photos = response.json()
                self.thumbnail_cache = {}
                self.display_photos()
                self.status_var.set(f"Found {len(self.current_photos)} photos for {search_date}")
            else:
                messagebox.showerror("Error", f"Failed to search photos: {response.status_code}")
        except Exception as e:
            messagebox.showerror("Error", f"Search error: {str(e)}")
    
    def display_photos(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        if not self.current_photos:
            ttk.Label(self.scrollable_frame, text="No photos found for this date").pack(pady=20)
            # Reset scroll position to top
            self.canvas.yview_moveto(0)
            return
        
        canvas_width = self.canvas.winfo_width() if hasattr(self, 'canvas') else 1200
        max_cols = self.calculate_grid_columns(canvas_width)
        
        self.current_columns = max_cols
        
        row = 0
        col = 0
        
        for i, photo in enumerate(self.current_photos):
            self.create_photo_thumbnail_cached(photo, row, col, i)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Reset scroll position to top after displaying photos
        self.root.after(100, lambda: self.canvas.yview_moveto(0))
    
    def create_photo_thumbnail_cached(self, photo, row, col, index):
        photo_frame = ttk.Frame(self.scrollable_frame, padding="5")
        photo_frame.grid(row=row, column=col, padx=5, pady=5)
        
        placeholder = tk.Label(photo_frame, text="Loading...", relief="sunken", bg="lightgray")
        placeholder.pack()
        
        info_text = f"Title: {photo.get('Title', 'Untitled')}\n"
        info_text += f"Time: {photo.get('TakenAtLocal', 'Unknown')}\n"
        info_text += f"Type: {photo.get('Type', 'Unknown')}"
        
        info_label = ttk.Label(photo_frame, text=info_text, wraplength=120, justify="left")
        info_label.pack(pady=(5, 0))
        
        select_btn = ttk.Button(
            photo_frame, 
            text="Select", 
            command=lambda p=photo, i=index: self.select_photo(p, i)
        )
        select_btn.pack(pady=(5, 0))
        
        photo_uid = photo.get('UID', '')
        if photo_uid in self.thumbnail_cache:
            cached_image = self.thumbnail_cache[photo_uid]
            placeholder.configure(image=cached_image, text="")
            setattr(placeholder, 'image', cached_image)
        else:
            threading.Thread(target=self.load_thumbnail_cached, args=(photo, placeholder), daemon=True).start()
    
    def load_thumbnail_cached(self, photo, placeholder_widget):
        try:
            files = photo.get("Files", [])
            if not files:
                return
            
            first_file = files[0]
            
            if first_file.get("Missing", False):
                placeholder_widget.configure(text="File Missing", bg="orange")
                return
            
            file_hash = first_file.get("Hash", "")
            if not file_hash:
                placeholder_widget.configure(text="No Hash", bg="lightcoral")
                return
            
            thumb_url = f"{self.photoprism_url}/api/v1/t/{file_hash}/{self.preview_token}/tile_500"
            response = requests.get(thumb_url)
            
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if 'svg' in content_type.lower() or len(response.content) < 1000:
                    placeholder_widget.configure(text="No Preview", bg="lightgray")
                    return
                
                try:
                    image = Image.open(io.BytesIO(response.content))
                    image.thumbnail((500, 500), Image.Resampling.LANCZOS)
                    photo_image = ImageTk.PhotoImage(image)
                    
                    photo_uid = photo.get('UID', '')
                    if photo_uid:
                        self.thumbnail_cache[photo_uid] = photo_image
                    
                    placeholder_widget.configure(image=photo_image, text="")
                    setattr(placeholder_widget, 'image', photo_image)
                    
                except Exception as img_error:
                    placeholder_widget.configure(text="Error", bg="lightcoral")
            else:
                placeholder_widget.configure(text="Failed", bg="lightcoral")
                
        except Exception as e:
            placeholder_widget.configure(text="Error", bg="lightcoral")
    
    def select_photo(self, photo, index):
        self.selected_photo = photo
        self.status_var.set(f"Selected photo: {photo.get('Title', 'Untitled')}")
    
    def get_selected_album_id(self):
        selected_album = self.album_var.get()
        if selected_album == "Root Album (No specific album)" or not selected_album:
            return ""
        
        # Extract album ID from the selected option
        for album_id, album_info in self.albums_dict.items():
            if selected_album == f"{album_info['title']} (ID: {album_id})":
                return album_id
        
        return ""
    
    def update_download_token_from_headers(self, headers):
        for header_name, header_value in headers.items():
            if "download" in header_name.lower() and "token" in header_name.lower():
                self.download_token = header_value
                break
    
    def download_original_photo(self, photo):
        try:
            photo_uid = photo.get('UID', '')
            if not photo_uid:
                raise Exception("No photo UID found")
            
            # Get photo details
            photo_detail_url = f"{self.photoprism_url}/api/v1/photos/{photo_uid}"
            headers = {
                "Authorization": f"Bearer {self.photoprism_token}",
                "Content-Type": "application/json"
            }
            
            detail_response = requests.get(photo_detail_url, headers=headers)
            self.update_download_token_from_headers(detail_response.headers)
            
            if detail_response.status_code != 200:
                raise Exception(f"Failed to get photo details: {detail_response.status_code}")
            
            photo_details = detail_response.json()
            
            # Extract file information
            files = photo_details.get("Files", [])
            if not files:
                raise Exception("No files found in photo details")
            
            primary_file = None
            for file_info in files:
                if file_info.get("Primary", False):
                    primary_file = file_info
                    break
            
            if not primary_file:
                primary_file = files[0]
            
            file_hash = primary_file.get("Hash", "")
            if not file_hash:
                raise Exception("No file hash found in photo details")
            
            # Try downloading with session download token
            if self.download_token:
                download_url = f"{self.photoprism_url}/api/v1/dl/{file_hash}?t={self.download_token}"
                response = requests.get(download_url)
                self.update_download_token_from_headers(response.headers)
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    
                    if ('image/' in content_type and 'svg' not in content_type) or \
                       'video/' in content_type or \
                       'application/octet-stream' in content_type:
                        
                        expected_size = primary_file.get('Size', 0)
                        actual_size = len(response.content)
                        
                        if (expected_size > 0 and actual_size >= (expected_size * 0.8)) or actual_size > 1000000:
                            filename = primary_file.get("Name", "photo.jpg")
                            return response.content, filename
            
            # Try other token approaches
            token_attempts = [
                self.preview_token,
                self.photoprism_token,
            ]
            
            for token in token_attempts:
                if not token:
                    continue
                
                # Try with token parameter
                download_url = f"{self.photoprism_url}/api/v1/dl/{file_hash}?t={token}"
                response = requests.get(download_url)
                self.update_download_token_from_headers(response.headers)
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    
                    if ('image/' in content_type and 'svg' not in content_type) or \
                       'video/' in content_type or \
                       'application/octet-stream' in content_type:
                        
                        expected_size = primary_file.get('Size', 0)
                        actual_size = len(response.content)
                        
                        if (expected_size > 0 and actual_size >= (expected_size * 0.8)) or actual_size > 1000000:
                            filename = primary_file.get("Name", "photo.jpg")
                            return response.content, filename
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '').lower()
                    
                    if ('image/' in content_type and 'svg' not in content_type) or \
                       'video/' in content_type or \
                       'application/octet-stream' in content_type:
                        
                        expected_size = primary_file.get('Size', 0)
                        actual_size = len(response.content)
                        
                        if (expected_size > 0 and actual_size >= (expected_size * 0.8)) or actual_size > 1000000:
                            filename = primary_file.get("Name", "photo.jpg")
                            return response.content, filename
            
            raise Exception("All download methods failed")
                
        except Exception as e:
            print(f"DEBUG: Error downloading photo: {e}")
            raise
    
    def get_photo_content_type(self, filename):
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
    
    def upload_to_lychee(self):
        if not self.selected_photo:
            messagebox.showerror("Error", "Please select a photo first")
            return
        
        if not self.lychee_session:
            messagebox.showerror("Error", "Please connect to Lychee first")
            return
        
        try:
            self.status_var.set("Downloading photo from PhotoPrism...")
            self.root.update()
            
            photo_data, filename = self.download_original_photo(self.selected_photo)
            
            self.status_var.set("Uploading photo to Lychee...")
            self.root.update()
            
            photo_title = self.selected_photo.get('Title', 'Untitled')
            content_type = self.get_photo_content_type(filename)
            
            xsrf_token = None
            for cookie in self.lychee_session.cookies:
                if cookie.name == "XSRF-TOKEN":
                    xsrf_token = urllib.parse.unquote(cookie.value or '')
                    break
            
            album_id = self.get_selected_album_id()
            
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
            
            upload_url = f"{self.lychee_url}/api/v2/Photo"
            
            response = self.lychee_session.post(
                upload_url,
                files=files,
                data=data,
                headers=headers
            )
            
            if response.status_code in [200, 201]:
                album_name = self.album_var.get()
                self.status_var.set(f"Successfully uploaded '{photo_title}' to {album_name}!")
                return
            
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
                
                response2 = self.lychee_session.post(
                    upload_url,
                    data=multipart_data,
                    headers=headers2
                )
                
                if response2.status_code in [200, 201]:
                    album_name = self.album_var.get()
                    self.status_var.set(f"Successfully uploaded '{photo_title}' to {album_name}!")
                    messagebox.showinfo("Success", f"Photo '{photo_title}' uploaded successfully to {album_name}!")
                    return
                    
            except ImportError:
                pass
            except Exception as e:
                print(f"DEBUG: Multipart encoder error: {e}")
            
            error_msg = f"Upload failed with status {response.status_code}"
            try:
                error_data = response.json()
                if 'message' in error_data:
                    error_msg += f": {error_data['message']}"
                elif 'errors' in error_data:
                    error_msg += f": {error_data['errors']}"
            except:
                error_msg += f": {response.text[:200]}"
            
            self.status_var.set(f"Upload failed: {error_msg}")
            messagebox.showerror("Upload Failed", error_msg)
        
        except Exception as e:
            error_msg = f"Upload error: {str(e)}"
            self.status_var.set(error_msg)
            messagebox.showerror("Error", error_msg)
            print(f"DEBUG: Upload exception: {e}")
    
    def load_lychee_albums(self):
        if not self.lychee_session:
            messagebox.showerror("Error", "Please connect to Lychee first")
            return
        
        try:
            # Get CSRF token for the request
            xsrf_token = None
            for cookie in self.lychee_session.cookies:
                if cookie.name == "XSRF-TOKEN":
                    xsrf_token = urllib.parse.unquote(cookie.value or '')
                    break
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            if xsrf_token:
                headers['X-XSRF-TOKEN'] = xsrf_token
            
            response = self.lychee_session.get(f"{self.lychee_url}/api/v2/Albums", headers=headers)
            
            if response.status_code == 200:
                albums_data = response.json()

                self.albums = []
                self.albums_dict = {}
                
                def parse_albums(albums_list, indent=0):
                    if isinstance(albums_list, dict):
                        albums_list = albums_list.get('albums', []) or albums_list.get('data', [])
                        if not albums_list and 'smart_albums' in albums_list:
                            albums_list = albums_list.get('smart_albums', []) + albums_list.get('tag_albums', []) + albums_list.get('albums', [])
                    
                    for album in albums_list:
                        if isinstance(album, dict):
                            album_id = album.get('id', '')
                            album_title = album.get('title', 'Untitled')
                            album_owner = album.get('owner_name', 'Unknown')
                            
                            # Store album info
                            album_info = {
                                'id': album_id,
                                'title': album_title,
                                'owner': album_owner,
                                'indent': indent
                            }
                            
                            self.albums.append(album_info)
                            self.albums_dict[album_id] = album_info
                            
                            # Parse nested albums
                            if 'albums' in album and album['albums']:
                                parse_albums(album['albums'], indent + 1)
                
                parse_albums(albums_data)

                album_options = ["Root Album (No specific album)"]
                
                for album in self.albums:
                    indent_str = "  " * album['indent']
                    option_text = f"{indent_str}{album['title']} (ID: {album['id']})"
                    album_options.append(option_text)
                
                self.album_dropdown['values'] = album_options
                
                current_selection = self.album_var.get()
                if current_selection not in album_options:
                    self.album_dropdown.set("Root Album (No specific album)")
                
                self.status_var.set(f"Loaded {len(self.albums)} albums from Lychee")
                messagebox.showinfo("Success", f"Loaded {len(self.albums)} albums from Lychee")
                
            else:
                error_msg = f"Failed to get albums: {response.status_code}"
                messagebox.showerror("Error", error_msg)
                
        except Exception as e:
            error_msg = f"Error loading albums: {str(e)}"
            print(f"DEBUG: {error_msg}")
            messagebox.showerror("Error", error_msg)
    
    def previous_day(self):
        current_date = datetime.strptime(self.date_var.get(), "%Y-%m-%d")
        previous_date = current_date - timedelta(days=1)
        self.date_var.set(previous_date.strftime("%Y-%m-%d"))
        self.search_photos()
    
    def next_day(self):
        current_date = datetime.strptime(self.date_var.get(), "%Y-%m-%d")
        next_date = current_date + timedelta(days=1)
        self.date_var.set(next_date.strftime("%Y-%m-%d"))
        self.search_photos()
    
    def save_config(self):
        config = {
            "photoprism_url": self.photoprism_url_var.get(),
            "photoprism_user": self.photoprism_user_var.get(),
            "photoprism_pass": self.photoprism_pass_var.get(),
            "lychee_url": self.lychee_url_var.get(),
            "lychee_user": self.lychee_user_var.get(),
            "lychee_pass": self.lychee_pass_var.get()
        }
        
        try:
            with open("photo_sync_config.json", "w") as f:
                json.dump(config, f, indent=2)
            messagebox.showinfo("Success", "Configuration saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {str(e)}")
    
    def load_config(self):
        try:
            if os.path.exists("photo_sync_config.json"):
                with open("photo_sync_config.json", "r") as f:
                    config = json.load(f)
                
                self.photoprism_url_var.set(config.get("photoprism_url", ""))
                self.photoprism_user_var.set(config.get("photoprism_user", ""))
                self.photoprism_pass_var.set(config.get("photoprism_pass", ""))
                self.lychee_url_var.set(config.get("lychee_url", ""))
                self.lychee_user_var.set(config.get("lychee_user", ""))
                self.lychee_pass_var.set(config.get("lychee_pass", ""))
                
                self.photoprism_url = config.get("photoprism_url", "")
                self.lychee_url = config.get("lychee_url", "")
                
        except Exception as e:
            print(f"Error loading config: {e}")

def main():
    root = tk.Tk()
    app = PhotoSyncApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()