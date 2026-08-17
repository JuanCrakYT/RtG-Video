"""
Animation sequence management for RtG Display.

Manages ordered sequences of animation frames with statistics.
"""

from typing import List, Dict, Set
from .frame import AnimationFrame


class AnimationSequence:
    """
    Represents a complete animation sequence.
    
    A sequence is an ordered list of frames that play in order.
    """
    
    def __init__(self):
        """Initialize an empty animation sequence."""
        self.frames: List[AnimationFrame] = []
    
    def add_frame(self, frame: AnimationFrame) -> int:
        """
        Add a frame to the end of the sequence.
        
        Args:
            frame: The AnimationFrame to add
            
        Returns:
            int: The index of the added frame
        """
        frame.frame_number = len(self.frames)
        self.frames.append(frame)
        return len(self.frames) - 1
    
    def insert_frame(self, index: int, frame: AnimationFrame) -> None:
        """
        Insert a frame at a specific position.
        
        Args:
            index: Position to insert at
            frame: The AnimationFrame to insert
        """
        self.frames.insert(index, frame)
        # Renumber all frames after insertion
        for i in range(index, len(self.frames)):
            self.frames[i].frame_number = i
    
    def remove_frame(self, index: int) -> AnimationFrame:
        """
        Remove a frame at a specific position.
        
        Args:
            index: Position to remove
            
        Returns:
            AnimationFrame: The removed frame
        """
        frame = self.frames.pop(index)
        # Renumber remaining frames
        for i in range(index, len(self.frames)):
            self.frames[i].frame_number = i
        return frame
    
    def get_frame(self, index: int) -> AnimationFrame:
        """Get a frame by index."""
        return self.frames[index]
    
    def get_total_duration(self) -> float:
        """Get total duration of the sequence."""
        return sum(frame.duration for frame in self.frames)
    
    def get_frame_count(self) -> int:
        """Get number of frames."""
        return len(self.frames)
    
    def get_pixel_statistics(self) -> Dict[str, Dict]:
        """
        Get statistics about pixel usage across the sequence.
        
        Returns:
            Dict mapping pixel UUID -> {
                'active_frames': count,
                'first_appearance': frame_index,
                'last_appearance': frame_index
            }
        """
        stats = {}
        
        for frame_idx, frame in enumerate(self.frames):
            for pixel_uuid in frame.active_pixels:
                if pixel_uuid not in stats:
                    stats[pixel_uuid] = {
                        'active_frames': 0,
                        'first_appearance': frame_idx,
                        'last_appearance': frame_idx
                    }
                
                stats[pixel_uuid]['active_frames'] += 1
                stats[pixel_uuid]['last_appearance'] = frame_idx
        
        return stats
    
    def __len__(self) -> int:
        """Get number of frames."""
        return len(self.frames)
    
    def __getitem__(self, index: int) -> AnimationFrame:
        """Get frame by index using array notation."""
        return self.frames[index]


class SequenceBuilder:
    """
    Builder pattern for creating AnimationSequence instances.
    """
    
    def __init__(self):
        """Initialize builder."""
        self.frames: List[AnimationFrame] = []
    
    def add_frame(self, frame: AnimationFrame) -> 'SequenceBuilder':
        """Add a frame."""
        self.frames.append(frame)
        return self
    
    def add_frames(self, frames: List[AnimationFrame]) -> 'SequenceBuilder':
        """Add multiple frames."""
        self.frames.extend(frames)
        return self
    
    def repeat_last_frame(self, count: int) -> 'SequenceBuilder':
        """
        Repeat the last frame a certain number of times.
        
        Args:
            count: Number of times to repeat
        """
        if self.frames:
            last_frame = self.frames[-1]
            for _ in range(count):
                # Create copies of the frame
                new_frame = AnimationFrame(last_frame.duration)
                new_frame.set_active_pixels(last_frame.get_active_pixels())
                self.frames.append(new_frame)
        return self
    
    def build(self) -> AnimationSequence:
        """Build and return the AnimationSequence."""
        sequence = AnimationSequence()
        for frame in self.frames:
            sequence.add_frame(frame)
        return sequence
