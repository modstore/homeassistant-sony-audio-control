# Sony Audio Control for Home Assistant

A Home Assistant custom integration for Sony AV receivers and audio devices that expose Sony's local JSON-RPC / ScalarWebAPI-style API.

The integration is designed to be model-friendly rather than model-locked: it asks the device what it supports, then creates Home Assistant entities from the settings the device reports.

Tested during initial development with a **Sony STR-DN1080**.

## Features

- Local control over your LAN. No cloud account required.
- UI setup through Home Assistant's Devices & Services screen.
- Configurable host and port. The default port is `10000`.
- Main `media_player` entity for receiver control where supported.
- Dynamic speaker-level controls as `number` entities.
- Dynamic sound settings as `select` or `switch` entities.
- Raw Sony API service for advanced testing and automations.
- Device dump service to help support new Sony models.
- HACS-compatible repository layout.

## Discovered entities

The exact entities depend on your Sony device and firmware. On the STR-DN1080, the integration can discover controls such as:

### Speaker settings

- Front L level
- Front R level
- Center level
- Surround L level
- Surround R level
- Surround back levels
- Subwoofer level
- Speaker selection

Unavailable channels reported by the receiver are skipped automatically.

### Sound settings

- Sound Field
- Pure Direct
- Sound Optimizer
- Calibration Type
- Custom Preset

### Advanced service

The `sony_audio_control.call_api` service lets advanced users call Sony methods directly before a polished entity exists.

## Installation

### Option 1: HACS custom repository

Until this integration is accepted into the default HACS repository list, install it as a custom repository:

1. Open **HACS**.
2. Go to **Integrations**.
3. Open the menu in the top-right corner.
4. Choose **Custom repositories**.
5. Add this repository URL:

   ```text
   https://github.com/modstore/homeassistant-sony-audio-control
   ```

6. Select category **Integration**.
7. Install **Sony Audio Control**.
8. Restart Home Assistant.
9. Go to **Settings → Devices & services → Add integration**.
10. Search for **Sony Audio Control**.

### Option 2: Manual install

Copy the integration folder so it exists at:

```text
/config/custom_components/sony_audio_control
```

Then restart Home Assistant and add the integration from **Settings → Devices & services**.

## Configuration

The setup flow asks for:

| Field | Required | Default | Notes |
|---|---:|---:|---|
| Host | Yes | — | The IP address or hostname of the receiver. |
| Port | No | `10000` | Most compatible Sony receivers appear to use this port. |

Example:

```text
Host: 192.168.1.14
Port: 10000
```

For best reliability, reserve a static IP address for the receiver in your router.

## Services

### `sony_audio_control.call_api`

Advanced/debug service for calling Sony JSON-RPC endpoints directly. The result is written to the Home Assistant log.

Example: read the subwoofer level:

```yaml
service: sony_audio_control.call_api
data:
  endpoint: audio
  method: getSpeakerSettings
  params:
    - target: subwooferLevel
```

Example: set the subwoofer level:

```yaml
service: sony_audio_control.call_api
data:
  endpoint: audio
  method: setSpeakerSettings
  params:
    - settings:
        - target: subwooferLevel
          value: "0.0"
```

If you have multiple Sony Audio Control devices configured, add `host` to target a specific receiver:

```yaml
service: sony_audio_control.call_api
data:
  host: 192.168.1.14
  endpoint: audio
  method: getSoundSettings
  params:
    - target: soundField
```

### `sony_audio_control.dump_device_info`

Writes a best-effort JSON dump of the receiver's supported APIs and discovered settings into your Home Assistant config directory.

```yaml
service: sony_audio_control.dump_device_info
data:
  host: 192.168.1.14
```

The output file will be named similar to:

```text
/config/sony_audio_control_192_168_1_14_dump.json
```

Attach that file to GitHub issues when requesting support for another Sony model.

## Troubleshooting

### The integration cannot connect

Check that the receiver is powered on or network-standby is enabled, then confirm the API responds from a terminal:

```bash
curl -s \
  -H "Content-Type: application/json" \
  -d '{"method":"getSupportedApiInfo","params":[{}],"id":1,"version":"1.0"}' \
  http://RECEIVER_IP:10000/sony/guide
```

### Enable debug logging

Add this to `configuration.yaml`, restart, then check the Home Assistant logs:

```yaml
logger:
  logs:
    custom_components.sony_audio_control: debug
```

## Supported devices

Known working / development-tested:

- Sony STR-DN1080

Likely compatible devices include other Sony receivers, soundbars, and audio products that expose the same local Sony JSON-RPC / ScalarWebAPI endpoints. Please open an issue with a device dump if you test another model.

## Development

Install development dependencies:

```bash
python -m pip install -r requirements_dev.txt
```

Run tests:

```bash
pytest
```

Run linting:

```bash
ruff check .
```

The tests include fixtures based on real STR-DN1080 API responses so discovery can be refactored without needing a receiver on the network.

## HACS release checklist for maintainers

For custom-repository installs, the current structure is enough:

- `hacs.json` exists at the repository root.
- `custom_components/sony_audio_control/manifest.json` exists.
- `manifest.json` has a unique `domain`, `version`, `documentation`, `issue_tracker`, and `codeowners`.
- The repository is public.

For cleaner public releases:

1. Commit the changes.
2. Push to GitHub.
3. Create a version tag, for example:

   ```bash
   git tag v0.1.5
   git push origin v0.1.5
   ```

4. Create a GitHub Release from that tag.
5. Install or update through HACS.

To eventually submit to the default HACS repository list, keep the repository public, maintain semantic versioned releases, document installation clearly, and respond to issues from users testing new devices.

## Credits

This integration was built around Sony's local JSON-RPC API behaviour and community experimentation with Sony audio devices.
