"""
Tests for RtG Display core functionality.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.rtg.uuid import UUIDManager, reset_uuid_manager
from src.rtg.cframe import CFrame, create_pixel_offset_cframe
from src.rtg.blocks import RtGBlock, RtGBuild, create_servo, create_part
from src.rtg.references import ReferenceManager, validate_references
from src.rtg.format import validate_build_json, get_build_stats
from src.display.pixel import Pixel, PixelTemplate
from src.display.matrix import DisplayMatrix, MatrixBuilder
from src.animation.frame import AnimationFrame, FrameBuilder
from src.animation.sequence import AnimationSequence, SequenceBuilder


def test_uuid_generation():
    """Test UUID generation and validation."""
    print("Testing UUID generation...")
    reset_uuid_manager()
    
    manager = UUIDManager()
    
    # Generate UUID
    uuid1 = manager.generate()
    assert manager.validate(uuid1), f"Generated UUID should be valid: {uuid1}"
    
    # Register UUID
    assert manager.register(uuid1), "Should register new UUID"
    assert not manager.register(uuid1), "Should not re-register same UUID"
    
    # Generate and register
    uuid2 = manager.generate_and_register((0, 0))
    assert manager.get_pixel_uuid(0, 0) == uuid2, "Should track pixel UUID"
    
    # Test invalid UUID format
    invalid_uuid = "not-a-uuid"
    assert not manager.validate(invalid_uuid), "Should reject invalid format"
    
    print("  ✓ UUID tests passed")


def test_cframe():
    """Test CFrame operations."""
    print("Testing CFrame...")
    
    # Identity CFrame
    cf_identity = CFrame.identity()
    assert cf_identity.data[0] == 0.0, "Identity should have zero position"
    assert cf_identity.data[3] == 1.0, "Identity should have 1 on diagonal"
    
    # Position CFrame
    cf_pos = CFrame.from_position(5.0, 10.0, 15.0)
    x, y, z = cf_pos.get_position()
    assert x == 5.0 and y == 10.0 and z == 15.0, "Position should match"
    
    # Pixel offset
    cf_pixel = create_pixel_offset_cframe(2, 3, 4.0)
    x, y, z = cf_pixel.get_position()
    assert x == 8.0 and y == 12.0, f"Pixel offset incorrect: {x}, {y}, {z}"
    
    # CFrame inverse
    cf_inv = cf_pos.inverse()
    cf_combined = cf_pos.multiply(cf_inv)
    x, y, z = cf_combined.get_position()
    assert abs(x) < 1e-5 and abs(y) < 1e-5 and abs(z) < 1e-5, "Multiply with inverse should be identity"
    
    print("  ✓ CFrame tests passed")


def test_blocks():
    """Test block creation and properties."""
    print("Testing blocks...")
    
    # Create blocks
    base = RtGBlock("Base")
    part = create_part([255, 0, 0])
    servo = create_servo()
    
    assert base.block_type == "Base", "Block type should match"
    assert part.properties["RGB"] == [255, 0, 0], "Part color should be set"
    
    # Add connections
    part.add_connection("1", "1", 0)
    assert len(part.connections) == 1, "Should have one connection"
    
    # Build
    build = RtGBuild()
    assert build.create_base() == 0, "Base should be at index 0"
    assert build.add_block(part) == 1, "Part should be at index 1"
    assert len(build) == 2, "Build should have 2 blocks"
    
    print("  ✓ Block tests passed")


def test_references():
    """Test reference system."""
    print("Testing references...")
    
    build = RtGBuild()
    base_idx = build.create_base()
    base = build.get_block(base_idx)
    
    child = create_part()
    child_idx = build.add_block(child)
    
    # Direct reference
    ReferenceManager.create_direct_reference(child, base_idx)
    assert len(child.connections) == 1, "Should have one connection"
    
    # Reference validation
    is_valid, errors = validate_references(build)
    assert is_valid, f"References should be valid, errors: {errors}"
    
    print("  ✓ Reference tests passed")


def test_pixel():
    """Test pixel creation and cloning."""
    print("Testing pixels...")
    
    # Create simple template
    template_build = RtGBuild()
    template_build.create_base()
    part = create_part([64, 64, 64])
    template_build.add_block(part)
    pixel_template = PixelTemplate(template_build)
    
    # Create target build
    target_build = RtGBuild()
    target_build.create_base()
    
    # Create pixel instance from template
    pixel, index_map = pixel_template.create_pixel_instance(
        x=0, y=0, target_build=target_build, base_index=0, spacing=4.0
    )
    
    assert pixel.x == 0 and pixel.y == 0, "Position should match"
    assert not pixel.active, "Should start inactive"
    
    # Set active
    pixel.activate()
    assert pixel.active, "Should be active after activation"
    
    # Deactivate
    pixel.deactivate()
    assert not pixel.active, "Should be inactive after deactivation"
    
    print("  ✓ Pixel tests passed")



def test_display_matrix():
    """Test display matrix creation."""
    print("Testing display matrix...")
    
    # Create pixel template
    pixel_build = RtGBuild()
    pixel_build.create_base()
    part = create_part([64, 64, 64])
    pixel_build.add_block(part)
    pixel_template = PixelTemplate(pixel_build)
    
    # Build 2x2 matrix
    matrix = (MatrixBuilder()
              .set_dimensions(2, 2)
              .set_template(pixel_template)
              .build())
    
    assert matrix.width == 2 and matrix.height == 2, "Dimensions should match"
    assert len(matrix.pixels) == 4, "Should have 4 pixels"
    
    # Test pixel access
    pixel = matrix.get_pixel(0, 0)
    assert pixel is not None, "Should get pixel at (0,0)"
    
    # Test activation
    assert matrix.set_pixel_active(0, 0, True), "Should activate pixel"
    assert len(matrix.get_active_pixels()) == 1, "Should have 1 active pixel"
    
    # Test stats
    stats = matrix.get_stats()
    assert stats["total_pixels"] == 4, "Stats should be correct"
    
    print("  ✓ Display matrix tests passed")


def test_animation():
    """Test animation frame and sequence."""
    print("Testing animation...")
    
    # Create frame
    frame = (FrameBuilder(duration=1.0)
             .set_frame_number(0)
             .build())
    
    frame.add_pixel("uuid1")
    frame.add_pixel("uuid2")
    
    assert frame.count_active() == 2, "Frame should have 2 active pixels"
    assert frame.duration == 1.0, "Duration should match"
    
    # Create another frame
    frame2 = (FrameBuilder(duration=0.5)
              .set_frame_number(1)
              .build())
    
    # Create sequence
    sequence = (SequenceBuilder()
                .add_frame(frame)
                .add_frame(frame2)
                .build())
    
    assert len(sequence) == 2, "Sequence should have 2 frames"
    assert abs(sequence.get_total_duration() - 1.5) < 0.001, "Total duration should be 1.5s"
    
    # Get pixel statistics
    pixel_stats = sequence.get_pixel_statistics()
    assert len(pixel_stats) == 2, "Should have 2 unique pixels"
    
    print("  ✓ Animation tests passed")



def test_format_validation():
    """Test JSON format validation."""
    print("Testing format validation...")
    
    # Valid build JSON
    valid_json = [
        ["Base", [], {}],
        ["Part", [["1", "1", 0]], {"RGB": [255, 0, 0]}]
    ]
    
    is_valid, error = validate_build_json(valid_json)
    assert is_valid, f"Valid JSON should pass: {error}"
    
    # Invalid: not an array
    invalid_json = {"type": "Base"}
    is_valid, error = validate_build_json(invalid_json)
    assert not is_valid, "Non-array should fail validation"
    
    # Invalid: bad parent index
    bad_json = [
        ["Base", [], {}],
        ["Part", [["1", "1", 999]], {}]  # Parent index out of range
    ]
    is_valid, error = validate_build_json(bad_json)
    assert not is_valid, "Out of range parent index should fail"
    
    print("  ✓ Format validation tests passed")


def run_all_tests():
    """Run all tests."""
    print("=" * 50)
    print("[TEST] Running RtG Display Tests")
    print("=" * 50)
    
    tests = [
        test_uuid_generation,
        test_cframe,
        test_blocks,
        test_references,
        test_pixel,
        test_display_matrix,
        test_animation,
        test_format_validation,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"  ✗ Test failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    print("=" * 50)
    print("[SUCCESS] All tests passed!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
