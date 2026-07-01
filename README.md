# Sony Audio Control for Home Assistant

A HACS-ready custom integration for Sony audio devices that expose Sony's local JSON-RPC / ScalarWebAPI style endpoints, including receivers such as the STR-DN1080.

This integration is designed to be dynamic: it queries the device for supported APIs and probes known Sony audio setting targets, then exposes only the controls that appear to be supported by the device.

## Features

- UI config flow
- Local polling, no cloud dependency
- Configurable host and port, default port `10000`
- Main `media_player` entity for power, volume, mute, and current input
- Dynamic `number` entities for supported speaker/audio levels
- Dynamic `select` entities for supported choice settings such as sound fields
- Dynamic `switch` entities for boolean settings such as mute or supported sound toggles
- Diagnostic sensors for model, power status, and current input
- Built-in diagnostics dump for GitHub issue reports
- Advanced `sony_audio_control.call_api` service for manual testing

## Installation for local testing

Copy this folder into Home Assistant so the integration exists at:

```text
/config/custom_components/sony_audio_control
```

Restart Home Assistant, then go to:

```text
Settings → Devices & services → Add integration → Sony Audio Control
```

For an STR-DN1080, the common settings are:

```text
Host: 192.168.1.14
Port: 10000
```

## HACS installation

Once the repository is pushed to GitHub:

1. Open HACS.
2. Add a custom repository.
3. Use `https://github.com/modstore/homeassistant-sony-audio-control`.
4. Choose category `Integration`.
5. Install and restart Home Assistant.

## Debugging

### Download diagnostics

Home Assistant supports integration diagnostics from the integration menu. Use this when opening an issue.

### Dump device info service

You can also call:

```yaml
service: sony_audio_control.dump_device_info
data:
  host: 192.168.1.14
```

This writes a file like this into `/config`:

```text
sony_audio_control_192_168_1_14_dump.json
```

Attach that file to GitHub issues when requesting support for new models.

### Manual API test service

Example:

```yaml
service: sony_audio_control.call_api
data:
  host: 192.168.1.14
  endpoint: audio
  method: getSpeakerSettings
  params:
    - target: subwooferLevel
```

## Notes

Sony's device APIs differ by model and firmware. This integration intentionally uses discovery and safe probing so it can grow beyond a single receiver model.

## Development

Recommended tools:

```bash
python -m pip install -r requirements_dev.txt
ruff check custom_components/sony_audio_control
```
