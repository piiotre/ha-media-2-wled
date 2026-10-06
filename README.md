# WLED Media Color Sync for Home Assistant

Pull the main colors out of a picture (album art, an `image` entity, a camera
snapshot, a URL or a local file) and stream them **in real time over UDP** to a
WLED device, rendered with animated effects.

## Features

- **Sources:** `media_player` album art, `image` entities, `camera` entities,
  HTTP(S) URLs and local files (the folder must be in `allowlist_external_dirs`).
- **Smart palette extraction:** each color is scored by how much of the picture
  it covers, how saturated it is and how bright it is. That stops black
  backgrounds from taking over. Near-duplicate colors are merged, then
  saturation and brightness get a boost so the colors look right on LEDs.
- **UDP protocols:** DDP (default, port 4048), DRGB (switches to DNRGB
  automatically on strips longer than 490 LEDs), DRGBW and WARLS (port 21324).
- **Effects:** Solid, Gradient, Segments, Ambient drift, Chase/flow, Twinkle and Breathe.
- **Smooth crossfade** when the song or picture changes.
- **Auto pause:** when the media player goes idle or off, streaming stops and
  WLED returns to its normal state.
- **Entities created per device:**
  - `switch` Color sync
  - `select` Effect
  - `number` Brightness and Effect speed
  - `sensor` Dominant color (the full palette is in its attributes)

## Installation (HACS)

1. HACS → ⋮ → *Custom repositories* → add this repo as type **Integration**.
2. Install **WLED Media Color Sync** and restart Home Assistant.
3. *Settings → Devices & Services → Add Integration → WLED Media Color Sync*.

Manual install: copy `custom_components/wled_color_sync` into your `config/custom_components/` folder.

## Setup

| Field | Notes |
|---|---|
| Host | IP address or hostname of the WLED device |
| Picture source | media_player / image / camera entity (optional, you can also use the services) |
| Protocol | DDP is recommended |
| Port | 0 = use the protocol's default port |
| LEDs | 0 = read the count from WLED automatically |

The options let you tune palette size, saturation/brightness boost, FPS,
transition time and stop-when-idle.

> In WLED, check that *Settings → Sync Interfaces → Realtime → Receive UDP realtime* is enabled.

## Services

### `wled_color_sync.sync_image`
Pushes the colors of any image to a device once. Returns the palette.

```yaml
action: wled_color_sync.sync_image
data:
  config_entry_id: 0123456789abcdef
  source: camera.front_door
```

### `wled_color_sync.extract_colors`
Only returns the palette; it doesn't touch any lights.

```yaml
action: wled_color_sync.extract_colors
data:
  source: media_player.spotify
  palette_size: 3
response_variable: result
# result.colors -> ["#e43f2a", "#1f6fd1", "#f2c14e"]
```

### Example: show a doorbell snapshot on the strip
```yaml
automation:
  - alias: Doorbell colors
    triggers:
      - trigger: state
        entity_id: image.doorbell_snapshot
    actions:
      - action: wled_color_sync.sync_image
        data:
          config_entry_id: 0123456789abcdef
          source: image.doorbell_snapshot
```
