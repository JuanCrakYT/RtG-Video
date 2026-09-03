"""
Display matrix management for RtG Display.

Handles a 2D grid of pixels with activation states and statistics.
"""

from typing import Iterable, List, Dict, Set, Tuple, Optional, Sequence
from .pixel import Pixel, PixelTemplate
from ..rtg.blocks import RtGBuild


MIN_CANVAS_DIMENSION = 1
MAX_CANVAS_DIMENSION = 128


class DisplayMatrix:
    """
    Represents a 2D display grid of pixels.
    """
    
    def __init__(
        self,
        width: int,
        height: int,
        pixel_template: PixelTemplate,
        palette: Optional[Iterable[Sequence[int]]] = None,
    ):
        """
        Initialize a display matrix.
        
        Args:
            width: Number of pixels horizontally
            height: Number of pixels vertically
            pixel_template: The PixelTemplate to use for cloning
        """
        if not isinstance(width, int) or not isinstance(height, int):
            raise TypeError("Canvas width and height must be integers")
        if not MIN_CANVAS_DIMENSION <= width <= MAX_CANVAS_DIMENSION:
            raise ValueError(f"Canvas width must be between {MIN_CANVAS_DIMENSION} and {MAX_CANVAS_DIMENSION}")
        if not MIN_CANVAS_DIMENSION <= height <= MAX_CANVAS_DIMENSION:
            raise ValueError(f"Canvas height must be between {MIN_CANVAS_DIMENSION} and {MAX_CANVAS_DIMENSION}")

        self.width = width
        self.height = height
        self.template = pixel_template
        self.build = RtGBuild()
        
        # Create Base block
        self.base_index = self.build.create_base()
        
        # 2D grid of pixels
        self.pixels: Dict[Tuple[int, int], Pixel] = {}
        self.pixel_layers: Dict[Tuple[int, int], List[Pixel]] = {}
        self.palette = (
            tuple(dict.fromkeys(
                tuple(int(channel) for channel in color)
                for color in palette
            ))
            if palette is not None else None
        )
        
        # Track active pixels
        self.active_pixels: Set[Tuple[int, int]] = set()
    
    def initialize_build(self, spacing: float = 1.0) -> int:
        """
        Initialize the build by creating all pixels.
        
        Args:
            spacing: Distance between pixels in RtG units
            
        Returns:
            int: Total number of blocks created
        """
        total_blocks = 1  # Base block
        
        for y in range(self.height):
            for x in range(self.width):
                colors = self.palette or (None,)
                layers = []
                for color in colors:
                    if color == (0, 0, 0):
                        continue
                    pixel, _ = self.template.create_pixel_instance(
                        x, y, self.build, self.base_index, spacing, color
                    )
                    layers.append(pixel)
                    total_blocks += pixel.get_block_count()
                self.pixel_layers[(x, y)] = layers
                if layers:
                    self.pixels[(x, y)] = layers[0]
        
        return total_blocks
    
    def get_pixel(self, x: int, y: int) -> Optional[Pixel]:
        """
        Get a pixel at grid position (x, y).
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            Pixel or None if out of bounds
        """
        return self.pixels.get((x, y))

    def get_pixels(self, x: int, y: int) -> List[Pixel]:
        """Get all physical color layers at a grid position."""
        return self.pixel_layers.get((x, y), [])

    def get_pixel_for_color(
        self,
        x: int,
        y: int,
        color: Sequence[int],
    ) -> Optional[Pixel]:
        """Get the physical layer assigned to a visible palette color."""
        target = tuple(int(channel) for channel in color)
        for pixel in self.get_pixels(x, y):
            splitter = next(
                block for block in pixel.blocks
                if block.block_type == "Splitter_3"
            )
            if tuple(splitter.properties.get("RGB", ())) == target:
                return pixel
        return None

    def iter_pixels(self):
        """Iterate over every physical pixel, including overlay layers."""
        for layers in self.pixel_layers.values():
            yield from layers
    
    def set_pixel_active(self, x: int, y: int, active: bool = True) -> bool:
        """
        Set a pixel's active state.
        
        Args:
            x: X coordinate
            y: Y coordinate
            active: Whether to activate or deactivate
            
        Returns:
            bool: True if successful, False if out of bounds
        """
        pixel = self.get_pixel(x, y)
        if pixel is None:
            return False
        
        pixel.set_active(active)
        
        if active:
            self.active_pixels.add((x, y))
        else:
            self.active_pixels.discard((x, y))
        
        return True
    
    def get_active_pixels(self) -> List[Tuple[int, int]]:
        """Get list of active pixel coordinates."""
        return list(self.active_pixels)
    
    def get_active_pixel_uuids(self) -> List[str]:
        """Get UUIDs of all active pixels."""
        uuids = []
        for x, y in self.active_pixels:
            pixel = self.get_pixel(x, y)
            if pixel:
                uuids.append(pixel.uuid)
        return uuids
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get statistics about the display.
        
        Returns:
            Dict with: width, height, total_pixels, active_pixels, total_blocks
        """
        total_blocks = 1  # Base
        for pixel in self.iter_pixels():
            total_blocks += pixel.get_block_count()
        
        return {
            "width": self.width,
            "height": self.height,
            "total_pixels": sum(
                len(layers) for layers in self.pixel_layers.values()
            ),
            "active_pixels": len(self.active_pixels),
            "total_blocks": total_blocks
        }
    
    def clear_active(self) -> None:
        """Deactivate all pixels."""
        for pixel in self.iter_pixels():
            pixel.deactivate()
        self.active_pixels.clear()


class MatrixBuilder:
    """
    Builder pattern for creating DisplayMatrix instances.
    """
    
    def __init__(self):
        """Initialize builder."""
        self.width = 8
        self.height = 8
        self.spacing = 1.0
        self.template = None
        self.palette = None
    
    def set_dimensions(self, width: int, height: int) -> 'MatrixBuilder':
        """Set matrix dimensions."""
        if not isinstance(width, int) or not isinstance(height, int):
            raise TypeError("Canvas width and height must be integers")
        if not MIN_CANVAS_DIMENSION <= width <= MAX_CANVAS_DIMENSION:
            raise ValueError(f"Canvas width must be between {MIN_CANVAS_DIMENSION} and {MAX_CANVAS_DIMENSION}")
        if not MIN_CANVAS_DIMENSION <= height <= MAX_CANVAS_DIMENSION:
            raise ValueError(f"Canvas height must be between {MIN_CANVAS_DIMENSION} and {MAX_CANVAS_DIMENSION}")
        self.width = width
        self.height = height
        return self
    
    def set_spacing(self, spacing: float) -> 'MatrixBuilder':
        """Set pixel spacing."""
        self.spacing = spacing
        return self
    
    def set_template(self, template: PixelTemplate) -> 'MatrixBuilder':
        """Set the pixel template."""
        self.template = template
        return self

    def set_palette(self, palette: Iterable[Sequence[int]]) -> 'MatrixBuilder':
        """Create one physical layer for each non-black palette color."""
        self.palette = tuple(dict.fromkeys(
            tuple(int(channel) for channel in color)
            for color in palette
        ))
        return self
    
    def build(self) -> DisplayMatrix:
        """Build and return the DisplayMatrix."""
        if self.template is None:
            raise ValueError("Template not set")
        
        matrix = DisplayMatrix(
            self.width,
            self.height,
            self.template,
            self.palette,
        )
        matrix.initialize_build(self.spacing)
        
        return matrix
