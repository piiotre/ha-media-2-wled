"""Constants for the WLED Media Color Sync integration."""

DOMAIN = "wled_color_sync"
MANUFACTURER = "WLED Media Color Sync"

PLATFORMS = ["switch", "select", "number", "sensor"]

# Config entry keys
CONF_HOST = "host"
CONF_NAME = "name"
CONF_PORT = "port"
CONF_PROTOCOL = "protocol"
CONF_NUM_LEDS = "num_leds"
CONF_SOURCE_ENTITY = "source_entity"
CONF_PALETTE_SIZE = "palette_size"
CONF_GAP_SIZE = "gap_size"
CONF_SATURATION_BOOST = "saturation_boost"
CONF_BRIGHTNESS_BOOST = "brightness_boost"
CONF_FPS = "fps"
CONF_TRANSITION = "transition"
CONF_STOP_WHEN_IDLE = "stop_when_idle"

# UDP protocols
PROTOCOL_DDP = "ddp"
PROTOCOL_DRGB = "drgb"
PROTOCOL_DRGBW = "drgbw"
PROTOCOL_WARLS = "warls"
PROTOCOLS = [PROTOCOL_DDP, PROTOCOL_DRGB, PROTOCOL_DRGBW, PROTOCOL_WARLS]

DEFAULT_PORTS = {
    PROTOCOL_DDP: 4048,
    PROTOCOL_DRGB: 21324,
    PROTOCOL_DRGBW: 21324,
    PROTOCOL_WARLS: 21324,
}

# Defaults
DEFAULT_PROTOCOL = PROTOCOL_DDP
DEFAULT_NUM_LEDS = 0  # 0 = auto-detect via WLED JSON API
DEFAULT_PALETTE_SIZE = 5
DEFAULT_GAP_SIZE = 0
DEFAULT_SATURATION_BOOST = 1.3
DEFAULT_BRIGHTNESS_BOOST = 1.0
DEFAULT_FPS = 30
DEFAULT_TRANSITION = 1.5  # seconds
DEFAULT_STOP_WHEN_IDLE = True
DEFAULT_BRIGHTNESS = 255
DEFAULT_SPEED = 50

# Seconds WLED waits after the last realtime packet before returning to normal
# mode (used by WARLS / DRGB / DRGBW; DDP uses WLED's own realtime timeout).
REALTIME_TIMEOUT = 2

# Effects
EFFECT_SOLID = "solid"
EFFECT_GRADIENT = "gradient"
EFFECT_SEGMENTS = "segments"
EFFECT_AMBIENT = "ambient"
EFFECT_CHASE = "chase"
EFFECT_TWINKLE = "twinkle"
EFFECT_BREATHE = "breathe"
EFFECT_GAP_BLOCKS = "gap_blocks"

EFFECTS = [
    EFFECT_SOLID,
    EFFECT_GRADIENT,
    EFFECT_SEGMENTS,
    EFFECT_AMBIENT,
    EFFECT_CHASE,
    EFFECT_TWINKLE,
    EFFECT_BREATHE,
    EFFECT_GAP_BLOCKS,
]
# Effects that do not change over time (sent at a reduced keep-alive rate)
STATIC_EFFECTS = {EFFECT_SOLID, EFFECT_GRADIENT, EFFECT_SEGMENTS, EFFECT_GAP_BLOCKS}
DEFAULT_EFFECT = EFFECT_GRADIENT

# Media player states considered "active"
ACTIVE_MEDIA_STATES = {"playing", "paused", "on", "buffering"}

# Services
SERVICE_SYNC_IMAGE = "sync_image"
SERVICE_EXTRACT_COLORS = "extract_colors"
ATTR_CONFIG_ENTRY_ID = "config_entry_id"
ATTR_SOURCE = "source"
ATTR_PALETTE_SIZE = "palette_size"
