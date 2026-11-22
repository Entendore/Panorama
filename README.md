# Panorama Creator

A single-file desktop application built with PySide6 and OpenCV for stitching multiple images into panoramas. Features a dark-themed UI, zoomable/pannable preview, configurable OpenCV stitching pipeline, synthetic test images, and auto-cropping of black borders.

---

## Features

- **Image Loading**: Add images via file dialog or drag-and-drop. The application remembers the last opened directory.
- **Image Management**: Drag-and-drop reordering in the list widget. Displays filename, dimensions, and file size for each item.
- **Keyboard Shortcuts**: `Delete`/`Backspace` to remove selected images, plus dedicated buttons for moving items up/down.
- **Background Stitching**: Runs `cv2.Stitcher` in a `QThread` (`StitchWorker`) to keep the UI responsive, with an indeterminate progress bar.
- **Configurable Pipeline**: Adjust stitching mode, confidence threshold, registration/compositing resolution, and wave correction.
- **Interactive Preview**: `PanoramaView` (based on `QGraphicsView`) supports scroll-wheel zoom (1.15x factor), right-click/middle-click drag to pan, fit-to-view, and 100% actual size.
- **Auto-Crop Black Borders**: Removes black edges using `cv2.findNonZero` and `cv2.boundingRect` with a 1-pixel safety pad.
- **Smart Crop Detection**: The crop button only enables if at least 25% of the pixels in a 5% image margin are below the intensity threshold.
- **Test Tab**: Generates 3 synthetic overlapping images (800px wide, 300px overlap on a 2200x500 canvas with gradients, shapes, and noise) for immediate testing.
- **High-Quality Save**: Exports via OpenCV (JPEG at 95% quality, PNG at compression level 3, TIFF, BMP) with a Qt fallback mechanism.
- **Busy Guard**: Prevents double-stitching while a worker thread is active.

---

## Requirements

| Package          | Minimum Version | Notes                                    |
|------------------|-----------------|------------------------------------------|
| Python           | 3.10+           | Required for `X \| Y` type hint syntax   |
| PySide6          | 6.x             | Qt for Python GUI framework              |
| OpenCV           | 4.x             | `opencv-python` or `opencv-python-headless` |
| NumPy            | 1.x             | Array operations                         |

### Install Dependencies

```bash
pip install PySide6 opencv-python numpy
```

---

## Quick Start

```bash
# Clone the repository
git clone https://github.com/Entendore/panorama.git
cd panorama

# Install dependencies
pip install -r requirements.txt

# Run the single-file application
python app.py
```

---

## Usage

### Main Tab

1. **Add Images**: Click "Add" in the toolbar, press `Ctrl+O`, or drag and drop files onto the window.
2. **Reorder**: Drag items in the image list, or use the "Up" / "Down" buttons.
3. **Remove**: Select an item and press `Delete`, or click "Remove". Use "Clear All" to reset.
4. **Configure**: Adjust the stitching parameters in the "Stitching Options" group box.
5. **Stitch**: Click "Stitch Panorama" or press `Ctrl+G`.
6. **Preview**: Use scroll-wheel to zoom, right-click drag to pan. Use "Fit", "100%", "+", and "-" buttons.
7. **Crop**: Click "Crop Borders" to remove black edges from the stitched result.
8. **Save**: Click "Save" in the toolbar or press `Ctrl+Shift+S`. Select format and destination.

### Test Tab

1. Switch to the "Test (3 Images)" tab. Three synthetic overlapping images are generated automatically.
2. Click any thumbnail to preview it.
3. Click "Stitch 3 Test Images" to execute the stitching pipeline.
4. Use the "Crop" button if the resulting panorama contains black borders.

---

## Stitching Parameters

| Parameter              | Default       | Range / Options      | Step  | Description                                                        |
|------------------------|---------------|----------------------|-------|--------------------------------------------------------------------|
| **Mode**               | Panorama      | Panorama, Scans      | -     | OpenCV stitcher mode                                               |
| **Confidence**         | 1.0           | 0.0 - 1.0            | 0.05  | Confidence threshold for seam finding                              |
| **Reg. Resolution**    | 0.6           | 0.1 - 1.0            | 0.1   | Registration resolution (lower is faster)                          |
| **Comp. Resolution**   | -1.0 (Full)   | -1.0 - 1.0           | 0.1   | Compositing resolution (-1.0 maps to full resolution)              |
| **Wave Correction**    | Enabled       | Enabled, Disabled    | -     | Compensates for wave distortion                                    |
| **Wave Kind**          | Horizontal    | Horizontal, Vertical | -     | Axis for wave correction                                           |

---

## Supported Formats

### Input
`.jpg`, `.jpeg`, `.png`, `.bmp`, `.tiff`, `.tif`, `.webp`

### Output
| Format | Settings                       |
|--------|--------------------------------|
| JPEG   | Quality: 95%                   |
| PNG    | Compression level: 3           |
| TIFF   | Lossless                       |
| BMP    | Uncompressed                   |

---

## Architecture

- **UI Layer**: Built with `PySide6`. Main window uses a `QSplitter` to separate the image list from the `PanoramaView`. A `QTabWidget` switches between the main creator and the test tab.
- **Threading**: `StitchWorker(QThread)` isolates the `cv2.Stitcher.stitch()` call. Communicates success/failure back to the main thread via a `Signal(bool, str, object)`.
- **Image Caching**: Loaded images are stored in dictionaries as both `np.ndarray` (BGR) and `QPixmap` to prevent redundant disk I/O and format conversions.
- **Auto-Crop Logic**: Converts the image to grayscale, applies a binary threshold (1), finds non-zero coordinates, calculates the bounding rectangle, and applies a 1-pixel pad before cropping.
- **Test Generation**: `generate_test_images()` creates a 2200x500 BGR canvas, draws gradients, shapes, and markers, then slices it into three 800px strips with a 300px overlap. Subtle tint and Gaussian noise are added per strip.

---

## Keyboard Shortcuts

| Shortcut       | Action                  |
|----------------|-------------------------|
| `Ctrl+O`       | Open file dialog        |
| `Ctrl+G`       | Stitch panorama         |
| `Ctrl+Shift+S` | Save panorama           |
| `Delete`       | Remove selected image   |
| `Backspace`    | Remove selected image   |

---

## Troubleshooting

| Error Message                                            | Solution                                                                 |
|----------------------------------------------------------|--------------------------------------------------------------------------|
| "Need more images or insufficient overlap."              | Provide at least 2 images with 20-30% overlap.                           |
| "Homography estimation failed..."                        | Use images with more distinct features/textures or increase overlap.     |
| "Camera parameter adjustment failed."                    | Try different stitching modes or lower the confidence threshold.         |
| Progress bar hangs / UI freezes                          | Ensure `opencv-python-headless` is used if running in specific environments. |
| Black borders remain after stitching                     | Click the "Crop Borders" button.                                         |

---