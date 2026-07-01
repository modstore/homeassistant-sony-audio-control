# Home Assistant Sony Audio Control

A HACS-ready custom integration for controlling Sony receivers/amplifiers that expose Sony's local REST/JSON-RPC style API, such as the Sony STR-DN1080.

This project is intentionally not tied to one model. It starts with a generic Sony API client and exposes useful Home Assistant entities where the device responds successfully.

## Current status

Early scaffold / alpha.

Implemented so far:

- UI config flow
- Host/IP configuration
- Optional port configuration, default `10000`
- Local polling API client
- Media player entity
  - Power on/off
  - Volume set
  - Mute
  - Source selection from discovered external inputs, where supported
- Number entities for common speaker level targets
  - Subwoofer level
  - Front left/right
  - Centre
  - Surround left/right
  - Surround back left/right
  - Height left/right
- Select entities for common sound settings
  - Sound field
  - Speaker pattern
- Sensors for power and playing content
- Mute switch

## Tested proof-of-concept

The STR-DN1080 responds to calls like:

```bash
curl -i -d '{ "method": "getSpeakerSettings", "id": 62, "params": [{"target": "subwooferLevel"}], "version": "1.0" }' \
  http://192.168.1.14:10000/sony/audio
```

And setting a value:

```bash
curl -i -d '{ "method": "setSpeakerSettings", "id": 62, "params": [{"settings": [{ "value": "0", "target": "subwooferLevel" }]}], "version": "1.0" }' \
  http://192.168.1.14:10000/sony/audio
```

## Installation via HACS custom repository

1. Upload this repository to GitHub as `homeassistant-sony-audio-control`.
2. In Home Assistant, open HACS.
3. Add a custom repository.
4. Use your GitHub repo URL.
5. Select category: `Integration`.
6. Install the integration.
7. Restart Home Assistant.
8. Go to **Settings → Devices & services → Add integration**.
9. Search for **Sony Audio Control**.
10. Enter the receiver/amplifier IP address and port.

## Manual installation

Copy this folder:

```text
custom_components/sony_audio_control
```

Into your Home Assistant config directory:

```text
/config/custom_components/sony_audio_control
```

Restart Home Assistant, then add the integration through the UI.

## Configuration

| Option | Required | Default | Example |
| --- | --- | --- | --- |
| Host/IP address | Yes | — | `192.168.1.14` |
| Port | No | `10000` | `10000` |

## Notes

On Sony receivers, local/network control may need to be enabled in the device settings. The option name varies by model, but it is often something like **Network Standby**, **Remote Start**, **External Control**, or **Control for HDMI/network**.

## Development notes

The API client is intentionally generic:

```python
await api.call("audio", "getSpeakerSettings", [{"target": "subwooferLevel"}], "1.0")
```

Future improvements:

- Better dynamic entity discovery from `getSupportedApiInfo`
- More complete STR-DN1080 target list
- Custom services for arbitrary Sony API calls
- Speaker distance entities
- EQ/band level entities
- Input icons and cleaner source names
- Diagnostics support
- Repairs/issues for failed optional targets

## Repository checklist before publishing

- Replace `@your-github-username` in `manifest.json`.
- Replace the documentation and issue tracker URLs in `manifest.json`.
- Add a real icon at `brands/sony_audio_control/icon.png` if submitting to default HACS.
- Create a GitHub release such as `v0.1.0`.
