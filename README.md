# IKEA OBEGRÄNSAD LED Control

⚠️⚠️ **Warning: This integration is in active development and may not yet support all features or devices. Use at your own risk.** ⚠️⚠️

_Note: This only works with modified IKEA OBEGRÄNSAD LED panels that use [this request](https://github.com/ph1p/ikea-led-obegraensad/pull/165) or later of the [IKEA OBEGRÄNSAD Hack/Mod
](https://github.com/ph1p/ikea-led-obegraensad) by [@ph1p](https://github.com/ph1p)_

A Home Assistant custom integration for controlling IKEA OBEGRÄNSAD LED displays via local network communication. This integration provides real-time control and monitoring of your modified IKEA OBEGRÄNSAD LED panel through WebSocket connections.

## Overview

![HA preview](preview.png)
![HA light](light.png)

The IKEA OBEGRÄNSAD LED Control integration enables seamless integration of modified IKEA OBEGRÄNSAD LED panels with Home Assistant. It communicates directly with the device over your local network using HTTP API calls and WebSocket connections for real-time updates.

### Features

- **Real-time Control**: Instant brightness adjustments and plugin switching
- **WebSocket Integration**: Live updates without polling delays
- **Multiple Entity Types**: Light, sensors, selects, and buttons
- **Device Management**: Plugin selection and rotation control
- **Schedule Monitoring**: Track active schedules and their status
- **Local Communication**: No cloud dependency, works entirely on your local network

## Supported Entities

This integration creates the following entities in Home Assistant:

### Light Entity

- **IKEA OBEGRÄNSAD LED Light**: Main light control with brightness adjustment
  - Supports transitions
  - Brightness control (0-255)
  - On/Off state management

### Sensor Entities

- **Rotation Sensor**: Current rotation angle of the display
- **Active Plugin Sensor**: Currently selected plugin/effect
- **Schedule Status Sensor**: Whether a schedule is currently active
- **Brightness Sensor**: Current brightness level as a sensor

### Select Entity

- **Plugin Select**: Dropdown to choose from available plugins/effects

### Button Entities

- **Rotate Left Button**: Rotate the display counterclockwise
- **Rotate Right Button**: Rotate the display clockwise

## Prerequisites

- Home Assistant 2023.1.0 or later
- A modified IKEA OBEGRÄNSAD LED panel with network connectivity
- The device must be accessible on your local network
- The device should have a web API endpoint available (typically on port 80)

## Installation

### HACS Installation (Recommended)

1. Open HACS in your Home Assistant instance
2. Navigate to "Integrations"
3. Click the three dots in the top right corner and select "Custom repositories"
4. Add this repository URL: `https://github.com/HennieLP/ikea-led-obegraensad-python-control`
5. Select "Integration" as the category
6. Click "Add"
7. Search for "IKEA OBEGRÄNSAD LED Control" in HACS
8. Click "Download"
9. Restart Home Assistant

### Manual Installation

1. Download the latest release from the [releases page](https://github.com/HennieLP/ikea-led-obegraensad-python-control/releases)
2. Extract the contents
3. Copy the `custom_components/ikea_obegraensad` folder to your Home Assistant's `custom_components` directory
4. The final path should be: `config/custom_components/ikea_obegraensad/`
5. Restart Home Assistant

## Configuration

### Adding the Integration

1. Go to **Settings** → **Devices & Services** in Home Assistant
2. Click **"+ ADD INTEGRATION"**
3. Search for **"IKEA OBEGRÄNSAD LED Control"**
4. Enter the IP address of your IKEA OBEGRÄNSAD LED device
   - Example: `192.168.1.100` or `192.168.5.60`
5. Click **Submit**

The integration will automatically discover and set up all available entities for your device.

### Finding Your Device IP Address

You can find your device's IP address through:

- Your router's admin interface
- Network scanning tools like `nmap`
- Home Assistant's network discovery
- Your device's configuration interface (if available)

## Usage Examples

### Basic Light Control

```yaml
# Turn on the light
service: light.turn_on
target:
  entity_id: light.ikea_obegraensad_led
data:
  brightness: 200

# Turn off the light
service: light.turn_off
target:
  entity_id: light.ikea_obegraensad_led
```

### Plugin Selection

```yaml
# Change to a specific plugin
service: select.select_option
target:
  entity_id: select.ikea_obegraensad_plugin
data:
  option: "Matrix Rain"
```

### Rotation Control

```yaml
# Rotate left
service: button.press
target:
  entity_id: button.ikea_obegraensad_rotate_left

# Rotate right
service: button.press
target:
  entity_id: button.ikea_obegraensad_rotate_right
```

### Automation Example

```yaml
automation:
  - alias: "LED Panel Evening Mode"
    trigger:
      - platform: sun
        event: sunset
    action:
      - service: select.select_option
        target:
          entity_id: select.ikea_obegraensad_plugin
        data:
          option: "Clock"
      - service: light.turn_on
        target:
          entity_id: light.ikea_obegraensad_led
        data:
          brightness: 100

  - alias: "LED Panel Night Mode"
    trigger:
      - platform: time
        at: "22:00:00"
    action:
      - service: light.turn_on
        target:
          entity_id: light.ikea_obegraensad_led
        data:
          brightness: 50
```

## API Endpoints

The integration communicates with your device using these endpoints:

- **HTTP API Base**: `http://[device_ip]/api`
- **WebSocket**: `ws://[device_ip]/ws`

### Expected Device API Response Format

The device should respond with JSON data containing:

```json
{
  "brightness": 150,
  "rotation": 0,
  "plugin": "Clock",
  "scheduleActive": false,
  "schedule": [],
  "plugins": ["Clock", "Matrix Rain", "Fire", "Rainbow"]
}
```

## Additional Services (Home Assistant)

This integration now provides several additional services to control scheduler, messages, storage and to fetch raw display data. Use them from Developer Tools → Services or in automations.

- `ikea_obegraensad.set_schedule` — set a schedule. Data: `schedule` (JSON or list of objects). Example:

```yaml
service: ikea_obegraensad.set_schedule
data:
  schedule:
    - pluginId: 3
      duration: 30
    - pluginId: 5
      duration: 60
```

- `ikea_obegraensad.clear_schedule`, `ikea_obegraensad.start_schedule`, `ikea_obegraensad.stop_schedule` — control schedule lifecycle.

- `ikea_obegraensad.add_message` — add a display message. Data: `text` (required), optional `repeat`, `id`, `delay`, `graph` (list), `miny`, `maxy`.

```yaml
service: ikea_obegraensad.add_message
data:
  text: "Hello"
  repeat: 1
  id: 99
```

- `ikea_obegraensad.remove_message` — remove message by `id`.

- `ikea_obegraensad.clear_storage` — clear device storage (if supported by firmware).

- `ikea_obegraensad.get_data` — fetch raw framebuffer (`/api/data`) and save it to Home Assistant config directory as `ikea_obegraensad_data.bin`.

Additionally, a UI Button entity `Persist Plugin` is available to persist the current plugin on the device (same as the `persist_plugin` service).

These services are implemented using the device HTTP API (where applicable) or WebSocket for real-time commands.

## Troubleshooting

### Connection Issues

1. **Cannot connect to device**:
   - Verify the IP address is correct
   - Ensure the device is powered on and connected to your network
   - Check that your Home Assistant can reach the device's network
   - Verify the device's web interface is accessible

2. **WebSocket connection problems**:
   - Check device logs for WebSocket server issues
   - Ensure no firewall is blocking WebSocket connections
   - Verify the device supports WebSocket on `/ws` endpoint

### Entity Not Updating

1. **Sensors not reflecting changes**:
   - Check WebSocket connection status in logs
   - Verify device is sending proper JSON format
   - Look for network connectivity issues

2. **Controls not working**:
   - Ensure device API accepts POST requests
   - Check device logs for API errors
   - Verify correct JSON payload format

### Debugging

Enable debug logging by adding this to your `configuration.yaml`:

```yaml
logger:
  default: info
  logs:
    custom_components.ikea_obegraensad: debug
```

Then check Home Assistant logs for detailed connection and communication information.

## Device Requirements

Your IKEA OBEGRÄNSAD LED device must:

1. Be connected to your local network
2. Run a web server (typically on port 80)
3. Provide HTTP API endpoints for control
4. Support WebSocket connections for real-time updates
5. Return JSON responses in the expected format

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/HennieLP/ikea-led-obegraensad-python-control/issues)
- **Discussions**: [GitHub Discussions](https://github.com/HennieLP/ikea-led-obegraensad-python-control/discussions)
- **Documentation**: [Project Wiki](https://github.com/HennieLP/ikea-led-obegraensad-python-control/wiki)

## Credits

- **Maintainers**: [@HennieLP](https://github.com/HennieLP), [@Pytonballoon810](https://github.com/Pytonballoon810)
- **Based on**: IKEA OBEGRÄNSAD LED hardware modifications
- **Home Assistant Integration**: Built using the official Home Assistant integration framework

---

**Note**: This integration requires a modified IKEA OBEGRÄNSAD LED panel with network connectivity. Standard IKEA OBEGRÄNSAD panels do not support network communication out of the box.
