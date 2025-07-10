import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from config import AppConfig, ConfigManager
from photoprism_client import PhotoPrismClient
from lychee_client import LycheeClient, LycheeAlbum
from photo_grid import PhotoGrid

class PhotoSyncApp:
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PhotoPrism to Lychee Daily Photo Sync")
        self.root.geometry("1400x1000")
        
        # Configuration and clients
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load_config()
        self.photoprism_client = PhotoPrismClient(self.config.photoprism)
        self.lychee_client = LycheeClient(self.config.lychee)
        
        # State
        self.selected_photo: Optional[Dict[str, Any]] = None
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.albums: list[LycheeAlbum] = []
        
        self.setup_ui()
        self.load_ui_from_config()
    
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configuration section
        self.setup_config_section(main_frame)
        
        # Date selection section
        self.setup_date_section(main_frame)
        
        # Photo grid section
        self.setup_photo_section(main_frame)
        
        # Action buttons section
        self.setup_action_section(main_frame)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Please configure connections and search for photos.")
        ttk.Label(main_frame, textvariable=self.status_var).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Configure grid weights for proper resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
    
    def setup_config_section(self, parent: ttk.Frame):
        config_frame = ttk.LabelFrame(parent, text="Configuration", padding="10")
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
    
    def setup_date_section(self, parent: ttk.Frame):
        date_frame = ttk.LabelFrame(parent, text="Date Selection", padding="10")
        date_frame.grid(row=1, column=0, columnspan=2, sticky="we", pady=(0, 10))
        
        ttk.Label(date_frame, text="Date:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.date_var = tk.StringVar(value=self.current_date)
        ttk.Entry(date_frame, textvariable=self.date_var, width=15).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Button(date_frame, text="Search Photos", command=self.search_photos).grid(row=0, column=2, padx=(0, 10))
        ttk.Button(date_frame, text="Previous Day", command=self.previous_day).grid(row=0, column=3, padx=(0, 5))
        ttk.Button(date_frame, text="Next Day", command=self.next_day).grid(row=0, column=4)
    
    def setup_photo_section(self, parent: ttk.Frame):
        photo_frame = ttk.LabelFrame(parent, text="Photo Selection", padding="10")
        photo_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=(0, 10))
        
        # Photo grid
        self.photo_grid = PhotoGrid(photo_frame, self.on_photo_select)
        
        # Configure grid weights
        photo_frame.columnconfigure(0, weight=1)
        photo_frame.rowconfigure(0, weight=1)
    
    def setup_action_section(self, parent: ttk.Frame):
        action_frame = ttk.Frame(parent)
        action_frame.grid(row=3, column=0, columnspan=2, sticky="we", pady=10)
        
        # Album selection dropdown
        ttk.Label(action_frame, text="Lychee Album:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.album_var = tk.StringVar()
        self.album_dropdown = ttk.Combobox(action_frame, textvariable=self.album_var, width=40, state="readonly")
        self.album_dropdown.grid(row=0, column=1, padx=(0, 10))
        
        # Initially populate with root album option
        self.album_dropdown['values'] = ["Root Album (No specific album)"]
        self.album_dropdown.set("Root Album (No specific album)")
        
        # Action buttons
        ttk.Button(action_frame, text="Upload Selected to Lychee", command=self.upload_to_lychee).grid(row=1, column=0, pady=(5, 0), padx=(0, 10))
        ttk.Button(action_frame, text="Load Albums", command=self.load_lychee_albums).grid(row=1, column=1, pady=(5, 0), padx=(0, 10))
        ttk.Button(action_frame, text="Save Config", command=self.save_config).grid(row=1, column=2, pady=(5, 0))
    
    def load_ui_from_config(self):
        self.photoprism_url_var.set(self.config.photoprism.url)
        self.photoprism_user_var.set(self.config.photoprism.username)
        self.photoprism_pass_var.set(self.config.photoprism.password)
        self.lychee_url_var.set(self.config.lychee.url)
        self.lychee_user_var.set(self.config.lychee.username)
        self.lychee_pass_var.set(self.config.lychee.password)
    
    def update_config_from_ui(self):
        self.config.photoprism.url = self.photoprism_url_var.get().rstrip('/')
        self.config.photoprism.username = self.photoprism_user_var.get()
        self.config.photoprism.password = self.photoprism_pass_var.get()
        self.config.lychee.url = self.lychee_url_var.get().rstrip('/')
        self.config.lychee.username = self.lychee_user_var.get()
        self.config.lychee.password = self.lychee_pass_var.get()
    
    def connect_photoprism(self):
        try:
            self.update_config_from_ui()
            self.config_manager.save_config(self.config, silent=True)
            
            # Update client with new config
            self.photoprism_client = PhotoPrismClient(self.config.photoprism)
            self.photoprism_client.connect()
            
            self.status_var.set("Connected to PhotoPrism successfully!")
            messagebox.showinfo("Success", "Connected to PhotoPrism!")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def connect_lychee(self):
        try:
            self.update_config_from_ui()
            self.config_manager.save_config(self.config, silent=True)
            
            # Update client with new config
            self.lychee_client = LycheeClient(self.config.lychee)
            self.lychee_client.connect()
            
            self.status_var.set("Connected to Lychee successfully!")
            messagebox.showinfo("Success", "Connected to Lychee!")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def search_photos(self):
        try:
            if not self.photoprism_client.tokens:
                messagebox.showerror("Error", "Please connect to PhotoPrism first")
                return
            
            search_date = self.date_var.get()
            photos = self.photoprism_client.search_photos(search_date)
            
            self.photo_grid.set_photos(photos)
            self.photo_grid.load_thumbnails_async(self.photoprism_client.get_thumbnail)
            
            self.status_var.set(f"Found {len(photos)} photos for {search_date}")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def on_photo_select(self, photo: Dict[str, Any], index: int):
        self.selected_photo = photo
        self.status_var.set(f"Selected photo: {photo.get('Title', 'Untitled')}")
    
    def upload_to_lychee(self):
        if not self.selected_photo:
            messagebox.showerror("Error", "Please select a photo first")
            return
        
        if not self.lychee_client.session:
            messagebox.showerror("Error", "Please connect to Lychee first")
            return
        
        try:
            self.status_var.set("Downloading photo from PhotoPrism...")
            self.root.update()
            
            photo_data, filename = self.photoprism_client.download_photo(self.selected_photo)
            
            self.status_var.set("Uploading photo to Lychee...")
            self.root.update()
            
            album_id = self.get_selected_album_id()
            success = self.lychee_client.upload_photo(photo_data, filename, album_id)
            
            if success:
                photo_title = self.selected_photo.get('Title', 'Untitled')
                album_name = self.album_var.get()
                self.status_var.set(f"Successfully uploaded '{photo_title}' to {album_name}!")
                messagebox.showinfo("Success", f"Photo '{photo_title}' uploaded successfully to {album_name}!")
            
        except Exception as e:
            error_msg = str(e)
            self.status_var.set(f"Upload failed: {error_msg}")
            messagebox.showerror("Upload Failed", error_msg)
    
    def load_lychee_albums(self):
        try:
            if not self.lychee_client.session:
                messagebox.showerror("Error", "Please connect to Lychee first")
                return
            
            self.albums = self.lychee_client.get_albums()
            
            # Update dropdown
            album_options = ["Root Album (No specific album)"]
            for album in self.albums:
                indent_str = "  " * album.indent
                option_text = f"{indent_str}{album.title} (ID: {album.id})"
                album_options.append(option_text)
            
            self.album_dropdown['values'] = album_options
            
            # Keep current selection if it still exists
            current_selection = self.album_var.get()
            if current_selection not in album_options:
                self.album_dropdown.set("Root Album (No specific album)")
            
            self.status_var.set(f"Loaded {len(self.albums)} albums from Lychee")
            messagebox.showinfo("Success", f"Loaded {len(self.albums)} albums from Lychee")
            
        except Exception as e:
            messagebox.showerror("Error", str(e))
    
    def get_selected_album_id(self) -> str:
        selected_album = self.album_var.get()
        if selected_album == "Root Album (No specific album)" or not selected_album:
            return ""
        
        # Extract album ID from the selected option
        for album in self.albums:
            if selected_album == f"{'  ' * album.indent}{album.title} (ID: {album.id})":
                return album.id
        
        return ""
    
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
        try:
            self.update_config_from_ui()
            self.config_manager.save_config(self.config)
            messagebox.showinfo("Success", "Configuration saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config: {str(e)}")


def main():
    root = tk.Tk()
    app = PhotoSyncApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()