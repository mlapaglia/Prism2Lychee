import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import io
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Callable


class PhotoGrid:
    def __init__(self, parent: tk.Widget, on_photo_select: Callable[[Dict[str, Any], int], None]):
        self.parent = parent
        self.on_photo_select = on_photo_select
        self.photos: List[Dict[str, Any]] = []
        self.thumbnail_cache: Dict[str, ImageTk.PhotoImage] = {}
        self.current_columns = 1
        self.selected_index: Optional[int] = None
        self.photo_frames: List[ttk.Frame] = []
        
        self.setup_ui()
    
    def setup_ui(self):
        self.canvas = tk.Canvas(self.parent, height=600)
        self.scrollbar = ttk.Scrollbar(self.parent, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.bind("<Configure>", self.on_canvas_resize)
        self.canvas.bind("<MouseWheel>", self.on_mouse_wheel)
        self.canvas.bind("<Button-4>", self.on_mouse_wheel)
        self.canvas.bind("<Button-5>", self.on_mouse_wheel)
        
        self.canvas.focus_set()
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.scrollbar.grid(row=0, column=1, sticky="ns")
        
        self.parent.columnconfigure(0, weight=1)
        self.parent.rowconfigure(0, weight=1)
    
    def set_photos(self, photos: List[Dict[str, Any]]):
        self.photos = photos
        self.thumbnail_cache.clear()
        self.selected_index = None
        self.photo_frames.clear()
        self.display_photos()
    
    def display_photos(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        self.photo_frames.clear()
        
        if not self.photos:
            ttk.Label(self.scrollable_frame, text="No photos found for this date").pack(pady=20)
            self.canvas.yview_moveto(0)
            return
        
        canvas_width = self.canvas.winfo_width() if hasattr(self, 'canvas') else 1200
        max_cols = self.calculate_grid_columns(canvas_width)
        self.current_columns = max_cols
        
        row, col = 0, 0
        
        for i, photo in enumerate(self.photos):
            photo_frame = self.create_photo_thumbnail(photo, row, col, i)
            self.photo_frames.append(photo_frame)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Reset scroll position to top
        self.parent.after(100, lambda: self.canvas.yview_moveto(0))
    
    def create_photo_thumbnail(self, photo: Dict[str, Any], row: int, col: int, index: int) -> ttk.Frame:
        photo_frame = ttk.Frame(self.scrollable_frame, padding="5")
        photo_frame.grid(row=row, column=col, padx=5, pady=5)
        
        clickable_frame = tk.Frame(photo_frame, relief="solid", borderwidth=2, bg="white")
        clickable_frame.pack(fill="both", expand=True)
        
        placeholder = tk.Label(clickable_frame, text="Loading...", relief="flat", bg="lightgray", cursor="hand2")
        placeholder.pack(padx=2, pady=2)
        
        info_text = self.format_photo_info(photo)
        info_label = tk.Label(clickable_frame, text=info_text, wraplength=120, justify="left", 
                             bg="white", cursor="hand2", font=("Arial", 8))
        info_label.pack(pady=(5, 5), padx=2)
        
        def on_click(event=None):
            self.select_photo(photo, index)
        
        clickable_frame.bind("<Button-1>", on_click)
        placeholder.bind("<Button-1>", on_click)
        info_label.bind("<Button-1>", on_click)
        
        # Bind scroll events to all widgets so scrolling works everywhere
        def bind_scroll_events(widget):
            widget.bind("<MouseWheel>", self.on_mouse_wheel)
            widget.bind("<Button-4>", self.on_mouse_wheel)
            widget.bind("<Button-5>", self.on_mouse_wheel)
        
        bind_scroll_events(photo_frame)
        bind_scroll_events(clickable_frame)
        bind_scroll_events(placeholder)
        bind_scroll_events(info_label)
        
        # Add hover effects
        def on_enter(event=None):
            if self.selected_index != index:
                clickable_frame.configure(bg="#f0f0f0")
                info_label.configure(bg="#f0f0f0")
        
        def on_leave(event=None):
            if self.selected_index != index:
                clickable_frame.configure(bg="white")
                info_label.configure(bg="white")
        
        clickable_frame.bind("<Enter>", on_enter)
        clickable_frame.bind("<Leave>", on_leave)
        placeholder.bind("<Enter>", on_enter)
        placeholder.bind("<Leave>", on_leave)
        info_label.bind("<Enter>", on_enter)
        info_label.bind("<Leave>", on_leave)
        
        # Store references for later access
        photo_frame.clickable_frame = clickable_frame # type: ignore
        photo_frame.info_label = info_label # type: ignore
        photo_frame.placeholder = placeholder # type: ignore
        photo_frame.photo_index = index # type: ignore
        
        # Load thumbnail asynchronously
        photo_uid = photo.get('UID', '')
        if photo_uid in self.thumbnail_cache:
            cached_image = self.thumbnail_cache[photo_uid]
            placeholder.configure(image=cached_image, text="")
            setattr(placeholder, 'image', cached_image)
        else:
            # Store placeholder reference for async loading
            placeholder.photo_data = photo # type: ignore
            placeholder.photo_uid = photo_uid # type: ignore
        
        return photo_frame
    
    def select_photo(self, photo: Dict[str, Any], index: int):
        # Clear previous selection
        if self.selected_index is not None and self.selected_index < len(self.photo_frames):
            old_frame = self.photo_frames[self.selected_index]
            if hasattr(old_frame, 'clickable_frame'):
                old_frame.clickable_frame.configure(bg="white", borderwidth=2, relief="solid") # type: ignore
                old_frame.info_label.configure(bg="white") # type: ignore
        
        # Set new selection
        self.selected_index = index
        if index < len(self.photo_frames):
            new_frame = self.photo_frames[index]
            if hasattr(new_frame, 'clickable_frame'):
                new_frame.clickable_frame.configure(bg="#e6f3ff", borderwidth=3, relief="solid") # type: ignore
                new_frame.info_label.configure(bg="#e6f3ff") # type: ignore # type: ignore
        
        # Call the callback
        self.on_photo_select(photo, index)
    
    def get_selected_photo(self) -> Optional[Dict[str, Any]]:
        if self.selected_index is not None and self.selected_index < len(self.photos):
            return self.photos[self.selected_index]
        return None
    def load_thumbnail(self, photo: Dict[str, Any], thumbnail_data: Optional[bytes], placeholder_widget: tk.Label):
        try:
            if not thumbnail_data:
                placeholder_widget.configure(text="No Preview", bg="lightgray")
                return
            
            # Create image from thumbnail data
            image = Image.open(io.BytesIO(thumbnail_data))
            image.thumbnail((500, 500), Image.Resampling.LANCZOS)
            photo_image = ImageTk.PhotoImage(image)
            
            # Cache the image
            photo_uid = photo.get('UID', '')
            if photo_uid:
                self.thumbnail_cache[photo_uid] = photo_image
            
            # Update placeholder
            placeholder_widget.configure(image=photo_image, text="", bg="white")
            setattr(placeholder_widget, 'image', photo_image)
            
        except Exception:
            placeholder_widget.configure(text="Error", bg="lightcoral")
    
    def load_thumbnails_async(self, thumbnail_loader: Callable[[Dict[str, Any]], Optional[bytes]]):
        def load_worker():
            # Create a list of photos that need thumbnails
            photos_to_load = []
            for photo_frame in self.photo_frames:
                if hasattr(photo_frame, 'placeholder'):
                    placeholder = photo_frame.placeholder # type: ignore
                    if hasattr(placeholder, 'photo_data'):
                        photo = placeholder.photo_data
                        photo_uid = placeholder.photo_uid
                        
                        if photo_uid not in self.thumbnail_cache:
                            photos_to_load.append((photo, photo_uid, placeholder))
            
            if not photos_to_load:
                return
            
            # Load thumbnails in parallel using ThreadPoolExecutor
            max_workers = min(8, len(photos_to_load))  # Limit to 8 concurrent downloads
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all thumbnail loading tasks
                future_to_photo = {
                    executor.submit(thumbnail_loader, photo): (photo, photo_uid, placeholder)
                    for photo, photo_uid, placeholder in photos_to_load
                }
                
                # Process completed downloads as they finish
                for future in as_completed(future_to_photo):
                    photo, photo_uid, placeholder = future_to_photo[future]
                    try:
                        thumbnail_data = future.result()
                        # Schedule UI update on main thread
                        self.parent.after(0, lambda p=photo, td=thumbnail_data, ph=placeholder: 
                                        self.load_thumbnail(p, td, ph))
                    except Exception as e:
                        # Handle individual thumbnail loading errors
                        self.parent.after(0, lambda ph=placeholder: 
                                        ph.configure(text="Error", bg="lightcoral"))
        
        threading.Thread(target=load_worker, daemon=True).start()
    
    def calculate_grid_columns(self, canvas_width: int) -> int:
        thumbnail_width = 520  # 500px image + 20px padding
        min_columns = 1
        max_columns = 6
        
        if canvas_width < thumbnail_width:
            return min_columns
        
        return max(min_columns, min(max_columns, canvas_width // thumbnail_width))
    
    def on_canvas_resize(self, event):
        if self.photos:
            self.parent.after(100, lambda: self.update_photo_layout(event.width))
    
    def update_photo_layout(self, canvas_width: int):
        new_columns = self.calculate_grid_columns(canvas_width)
        
        if self.current_columns != new_columns:
            self.current_columns = new_columns
            # Store currently selected photo before redisplaying
            selected_photo = self.get_selected_photo()
            self.display_photos()
            # Re-select the photo if it was selected before
            if selected_photo and self.selected_index is not None:
                self.select_photo(selected_photo, self.selected_index)
    
    def on_mouse_wheel(self, event):
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")
    
    def format_photo_info(self, photo: Dict[str, Any]) -> str:
        info_text = f"Title: {photo.get('Title', 'Untitled')}\n"
        info_text += f"Time: {photo.get('TakenAtLocal', 'Unknown')}\n"
        info_text += f"Type: {photo.get('Type', 'Unknown')}"
        return info_text