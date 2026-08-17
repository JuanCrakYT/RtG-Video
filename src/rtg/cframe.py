"""
CFrame utilities for RtG Display.

Handles creation, manipulation, and validation of CFrame transformations.
CFrame is a 12-element array: [X, Y, Z, R1, R2, R3, R4, R5, R6, R7, R8, R9]
where first 3 elements are position and remaining 9 form a rotation matrix.
"""

from typing import List, Tuple
import math


class CFrame:
    """
    Represents a Coordinate Frame (CFrame) transformation.
    
    Data structure: [X, Y, Z, R1, R2, R3, R4, R5, R6, R7, R8, R9]
    - Position: [X, Y, Z]
    - Rotation matrix 3x3: [R1 R2 R3]
                           [R4 R5 R6]
                           [R7 R8 R9]
    """
    
    def __init__(self, data: List[float] = None):
        """
        Initialize a CFrame.
        
        Args:
            data: List of 12 floats [X, Y, Z, R1-R9] or None for identity
        """
        if data is None:
            # Identity CFrame
            self.data = [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        else:
            if len(data) != 12:
                raise ValueError(f"CFrame data must have exactly 12 elements, got {len(data)}")
            self.data = [float(v) for v in data]
    
    @staticmethod
    def identity() -> 'CFrame':
        """Create an identity CFrame (no rotation or translation)."""
        return CFrame()
    
    @staticmethod
    def from_position(x: float, y: float, z: float) -> 'CFrame':
        """
        Create a CFrame with only position (identity rotation).
        
        Args:
            x, y, z: Position components
            
        Returns:
            CFrame: A translation-only CFrame
        """
        return CFrame([x, y, z, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0])
    
    @staticmethod
    def from_position_and_rotation(
        x: float, y: float, z: float,
        euler_x: float = 0.0,
        euler_y: float = 0.0,
        euler_z: float = 0.0
    ) -> 'CFrame':
        """
        Create a CFrame from position and Euler angles (degrees).
        
        Args:
            x, y, z: Position
            euler_x, euler_y, euler_z: Rotation in degrees
            
        Returns:
            CFrame: The combined transformation
        """
        # Convert degrees to radians
        rx = math.radians(euler_x)
        ry = math.radians(euler_y)
        rz = math.radians(euler_z)
        
        # Calculate rotation matrix components (ZYX convention - RtG standard)
        cos_x = math.cos(rx)
        sin_x = math.sin(rx)
        cos_y = math.cos(ry)
        sin_y = math.sin(ry)
        cos_z = math.cos(rz)
        sin_z = math.sin(rz)
        
        # ZYX rotation matrix
        r1 = cos_y * cos_z
        r2 = sin_x * sin_y * cos_z - cos_x * sin_z
        r3 = cos_x * sin_y * cos_z + sin_x * sin_z
        
        r4 = cos_y * sin_z
        r5 = sin_x * sin_y * sin_z + cos_x * cos_z
        r6 = cos_x * sin_y * sin_z - sin_x * cos_z
        
        r7 = -sin_y
        r8 = sin_x * cos_y
        r9 = cos_x * cos_y
        
        return CFrame([x, y, z, r1, r2, r3, r4, r5, r6, r7, r8, r9])
    
    def get_position(self) -> Tuple[float, float, float]:
        """Get the position components (x, y, z)."""
        return (self.data[0], self.data[1], self.data[2])
    
    def get_rotation_matrix(self) -> List[List[float]]:
        """
        Get the rotation matrix as a 3x3 matrix.
        
        Returns:
            List[List[float]]: 3x3 rotation matrix
        """
        return [
            [self.data[3], self.data[4], self.data[5]],
            [self.data[6], self.data[7], self.data[8]],
            [self.data[9], self.data[10], self.data[11]]
        ]
    
    def to_list(self) -> List[float]:
        """Return the CFrame as a list of 12 floats."""
        return self.data.copy()
    
    def multiply(self, other: 'CFrame') -> 'CFrame':
        """
        Multiply this CFrame with another (composition).
        
        This represents applying another transformation after this one.
        
        Args:
            other: Another CFrame
            
        Returns:
            CFrame: The result of self * other
        """
        # Extract components
        x1, y1, z1 = self.data[0:3]
        m1 = self.get_rotation_matrix()
        
        x2, y2, z2 = other.data[0:3]
        m2 = other.get_rotation_matrix()
        
        # Position = self.pos + self.rot * other.pos
        new_x = x1 + m1[0][0]*x2 + m1[0][1]*y2 + m1[0][2]*z2
        new_y = y1 + m1[1][0]*x2 + m1[1][1]*y2 + m1[1][2]*z2
        new_z = z1 + m1[2][0]*x2 + m1[2][1]*y2 + m1[2][2]*z2
        
        # Rotation = self.rot * other.rot
        new_rot = []
        for i in range(3):
            for j in range(3):
                val = sum(m1[i][k] * m2[k][j] for k in range(3))
                new_rot.append(val)
        
        return CFrame([new_x, new_y, new_z] + new_rot)
    
    def inverse(self) -> 'CFrame':
        """
        Get the inverse transformation.
        
        Returns:
            CFrame: The inverse of this CFrame
        """
        # For rotation matrix, inverse = transpose
        m = self.get_rotation_matrix()
        m_inv = [[m[j][i] for j in range(3)] for i in range(3)]
        
        # Inverse position = -rot_inv * pos
        x, y, z = self.data[0:3]
        inv_x = -(m_inv[0][0]*x + m_inv[0][1]*y + m_inv[0][2]*z)
        inv_y = -(m_inv[1][0]*x + m_inv[1][1]*y + m_inv[1][2]*z)
        inv_z = -(m_inv[2][0]*x + m_inv[2][1]*y + m_inv[2][2]*z)
        
        rot_flat = []
        for i in range(3):
            for j in range(3):
                rot_flat.append(m_inv[i][j])
        
        return CFrame([inv_x, inv_y, inv_z] + rot_flat)
    
    def __repr__(self) -> str:
        """String representation of CFrame."""
        x, y, z = self.data[0:3]
        return f"CFrame({x:.2f}, {y:.2f}, {z:.2f})"


def create_pixel_offset_cframe(x: int, y: int, spacing: float = 4.0) -> CFrame:
    """
    Create a CFrame offset for placing a pixel at grid position (x, y).
    
    Args:
        x: Grid X position
        y: Grid Y position
        spacing: Distance between pixels in RtG units
        
    Returns:
        CFrame: Position offset for the pixel
    """
    pos_x = x * spacing
    pos_y = y * spacing
    pos_z = 0.0
    
    return CFrame.from_position(pos_x, pos_y, pos_z)
