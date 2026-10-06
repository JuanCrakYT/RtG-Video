// Minimal rangetouch stub - provides touch support for range inputs
// This is a no-op stub since we don't need full touch range support

const RangeTouch = {
    setup(input) {
        // No-op - touch range support not needed for RtG preview
    },
    destroy(input) {
        // No-op
    },
};

export default RangeTouch;