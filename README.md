# PhotoSync - PhotoPrism to Lychee Sync Tool

A clean, modular Python application for syncing photos from PhotoPrism to Lychee galleries.

## Features

- **Easy Configuration**: Simple UI for setting up PhotoPrism and Lychee connections
- **Date-based Search**: Browse photos by specific dates
- **Visual Photo Grid**: Responsive thumbnail grid with async loading
- **Album Management**: Upload photos to specific Lychee albums
- **Robust Download**: Multiple fallback methods for photo downloading
- **Clean Architecture**: Modular design for easy maintenance and extension

## Installation

1. Clone or download the project files
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the application:
```bash
python main.py
```

### Setup Process

1. **Configure Connections**:
   - Enter your PhotoPrism URL and credentials
   - Enter your Lychee URL and credentials
   - Click "Connect PhotoPrism" and "Connect Lychee"

2. **Browse Photos**:
   - Select a date using the date picker
   - Click "Search Photos" to load thumbnails
   - Use "Previous Day" / "Next Day" for easy navigation

3. **Upload Photos**:
   - Click "Select" on any photo thumbnail
   - Choose a destination album (or use root album)
   - Click "Upload Selected to Lychee"

4. **Save Configuration**:
   - Click "Save Config" to persist your settings

## File Structure

```
photo_sync/
├── main.py                 # Main application entry point
├── config.py              # Configuration management
├── photoprism_client.py   # PhotoPrism API client
├── lychee_client.py       # Lychee API client
├── photo_grid.py          # Photo grid widget
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

## Architecture

The application follows a clean, modular architecture:

- **`main.py`**: Main application class and UI setup
- **`config.py`**: Configuration management with dataclasses
- **`photoprism_client.py`**: Handles all PhotoPrism API interactions
- **`lychee_client.py`**: Manages Lychee API communication
- **`photo_grid.py`**: Reusable photo grid widget with async thumbnail loading

## Key Improvements

✅ **Separation of Concerns**: Each module has a single responsibility
✅ **Type Safety**: Uses type hints throughout
✅ **Error Handling**: Comprehensive error handling with user-friendly messages
✅ **Async Loading**: Non-blocking thumbnail loading
✅ **Responsive Design**: Grid adapts to window size
✅ **Clean APIs**: Well-defined interfaces between components
✅ **Configuration Management**: Structured config with validation

## Requirements

- Python 3.7+
- tkinter (usually included with Python)
- requests
- Pillow (PIL)
- requests-toolbelt (optional, for better upload handling)

## Troubleshooting

### Connection Issues
- Ensure URLs don't have trailing slashes
- Check that credentials are correct
- Verify network connectivity to both services

### Upload Issues
- Ensure you're connected to both services
- Check that the selected album exists
- Verify file permissions and sizes

### Photo Loading Issues
- Some photos may not have thumbnails available
- Check PhotoPrism's file indexing status
- Verify file formats are supported

## Future Enhancements

- Batch upload functionality
- Progress bars for long operations
- Photo metadata preservation
- Automatic daily sync scheduling
- Support for additional photo services