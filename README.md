# Sony Audio Control for Home Assistant

A HACS-ready custom integration for Sony receivers, amplifiers, soundbars, and speakers that expose Sony's local ScalarWebAPI / SongPal-style REST API.

This project started with a Sony STR-DN1080, but the integration is intentionally **not model locked**. It discovers supported API methods and probes known setting targets so it can expose only the entities your device actually supports.

## Features

- UI config flow
- Local polling, no cloud account required
- Configurable host and port, default port `10000`
- Media player entity for power, volume, mute and inputs where available
- Dynamic number entities for speaker/sound levels, including subwoofer level
- Dynamic select entities for supported sound/input/playback settings
- Sensors for model, API support, power status, inputs and active settings
- Switches for mute and supported boolean settings
- Service to call any raw Sony API method for testing new devices

## Installation for testing

Copy this folder into Home Assistant:

```text
/config/custom_components/sony_audio_control
```

Restart Home Assistant, then add the integration from:

```text
Settings → Devices & services → Add integration → Sony Audio Control
```

Use your receiver/amplifier IP address and port `10000` unless your device uses a different port.

## HACS installation

Once this is pushed to GitHub:

1. HACS → Custom repositories
2. Add your repository URL
3. Category: Integration
4. Install **Sony Audio Control**
5. Restart Home Assistant
6. Add the integration from Devices & services

## Development notes

The integration first calls `/sony/guide` with `getSupportedApiInfo`. Then it probes supported methods/settings. This allows newer or different Sony devices to work without adding model-specific files.

For STR-DN1080 testing, the known working proof-of-concept commands were:

```bash
curl -i -d '{ "method": "setSpeakerSettings", "id": 62, "params": [{"settings": [{ "value": "0", "target": "subwooferLevel" }]}], "version": "1.0"}' http://192.168.1.14:10000/sony/audio

curl -i -d '{ "method": "getSpeakerSettings", "id": 62, "params": [{"target": "subwooferLevel"}], "version": "1.0"}' http://192.168.1.14:10000/sony/audio
```

## Raw API service

This integration registers a service for experimenting with new devices/settings:

```yaml
service: sony_audio_control.call_method
data:
  entry_id: YOUR_CONFIG_ENTRY_ID
  service: audio
  method: getSpeakerSettings
  params:
    - target: subwooferLevel
  version: "1.0"
```

The response is written to the Home Assistant log.

## Status

Early development scaffold. Expect first-device testing and fixes.
