# AGENTS.md

Guidance for coding agents working on this Home Assistant custom integration.

## Project

Repository: `homeassistant-sony-audio-control`

Integration domain: `sony_audio_control`

Purpose: Home Assistant custom integration for Sony AV receivers/audio devices using Sony's local JSON-RPC API.

Primary tested device: Sony STR-DN1080.

The integration should remain model-agnostic where possible by using Sony discovery and self-describing settings responses.

## Core Principles

1. Preserve existing user-facing behaviour unless explicitly asked otherwise.
2. Do not break existing entity IDs, unique IDs, services, config flow, or diagnostics.
3. Prefer dynamic discovery over model-specific hard-coding.
4. Keep Sony API parsing out of Home Assistant entity classes.
5. Entities should read state from the coordinator cache, not call Sony directly.
6. Writes should go through coordinator mutation methods so the UI can update optimistically.
7. Avoid unnecessary network requests.
8. Add or update tests for every behaviour change.

## Architecture

Preferred flow:

```text
Sony API Client
    ↓
Sony models / parsers
    ↓
Coordinator cache
    ↓
Home Assistant entities
```

### Sony Client

The Sony client should handle:

- HTTP JSON-RPC calls
- Sony API error handling
- Parsing Sony responses into integration models
- Known Sony request quirks

The client should not import Home Assistant modules.

### Models

Sony models should live in the Sony layer and remain pure Python.

Useful model concepts:

- `SonyState`
- `SonySetting`
- `SonyVolume`
- `SonySystem`
- source/input models if applicable

### Coordinator

The coordinator is the single source of truth for entity state.

Normal refresh should update cached state from Sony.

Entities must not call the Sony client directly for polling.

Writes should be exposed via coordinator methods such as:

```python
async_set_speaker_setting(...)
async_set_sound_setting(...)
async_set_volume(...)
async_set_mute(...)
async_select_source(...)
```

Each write method should:

1. Call the Sony API.
2. Only update cache after the API succeeds.
3. Call `async_update_listeners()` so the UI updates immediately.
4. Not force a full refresh after every set unless specifically required.

## Sony API Notes

The STR-DN1080 has confirmed behaviour:

### Supported API discovery

`guide/getSupportedApiInfo` requires:

```json
{"params": [{}], "version": "1.0"}
```

### Speaker settings

`audio/getSpeakerSettings` with:

```json
{"params": [{}], "version": "1.0"}
```

returns all speaker settings, including numeric and enum targets.

Use this response to dynamically create number/select entities.

### Sound settings

`audio/getSoundSettings` with:

```json
{"params": [{}], "version": "1.1"}
```

returns sound fields, Pure Direct, calibration type, sound optimizer, custom presets, etc.

Use this response to dynamically create select/switch entities.

### Volume information

`audio/getVolumeInformation` should be called with:

```json
{"params": [{}], "version": "1.1"}
```

The primary output for the tested receiver is:

```text
extOutput:zone?zone=1
```

Mute is returned as a string:

```json
"mute": "on"
```

or:

```json
"mute": "off"
```

Do not use `bool("off")`; it evaluates to `True`.

Correct parsing:

```python
muted = mute_raw.lower() == "on"
```

### Setting mute

The STR-DN1080 expects:

```json
{"mute": "on"}
```

or:

```json
{"mute": "off"}
```

Do not send:

```json
{"status": true}
```

Do not include `target` unless a future verified model requires it.

### Source selection

`avContent/setPlayContent` should use version `1.2` where supported.

## Entity Guidelines

### Entity IDs and Unique IDs

Do not change existing entity IDs or unique ID construction unless explicitly requested.

This is critical for existing dashboards, automations, and helpers.

### Availability

Entities should become unavailable when the coordinator cannot communicate with the receiver and recover automatically when communication resumes.

Do not spam logs on repeated connection failures.

### Optimistic Updates

After a successful set action, update the coordinator cache immediately.

Example:

```python
await self.client.set_speaker_setting(target, value)
self.state.speaker_settings[target].current_value = value
self.async_update_listeners()
```

Do not call a full coordinator refresh after every set just to update the UI.

Polling should still eventually confirm and correct state if the receiver was changed externally.

## Diagnostics

Diagnostics should help debug devices the maintainer does not own.

Include:

- integration version
- config entry metadata, redacted as appropriate
- supported API info
- discovery successes/failures
- cached state
- speaker settings
- sound settings
- volume info
- system info
- source list
- API call timings
- Sony error codes for failed probes

Redact sensitive data where appropriate.

MAC addresses may be included when useful for Home Assistant device registry, but avoid exposing secrets, tokens, or credentials.

## Services

Keep existing services stable.

Important services:

- `sony_audio_control.call_api`
- `sony_audio_control.reload`
- diagnostics/dump service if present

Service handlers should support multiple config entries where appropriate.

## HACS Requirements

Maintain HACS-compatible layout:

```text
custom_components/sony_audio_control/
hacs.json
README.md
LICENSE
```

`manifest.json` must include at least:

- `domain`
- `name`
- `version`
- `config_flow`
- `documentation`
- `issue_tracker`
- `codeowners`
- `iot_class`

Do not commit IDE files, caches, or local environment files.

Recommended `.gitignore` entries:

```gitignore
.idea/
.vscode/
__pycache__/
*.pyc
.pytest_cache/
.mypy_cache/
.ruff_cache/
.venv/
```

## Testing

Run tests before finalising changes.

Expected commands may include:

```bash
pytest
ruff check .
python -m compileall custom_components/sony_audio_control tests
```

Add tests for:

- Sony response parsing
- setting discovery
- entity factory mapping
- coordinator refresh
- optimistic updates
- mute parsing and writing
- source selection
- diagnostics output
- reload service
- error handling/recovery

When fixing a bug, add a regression test.

## Style

Follow Home Assistant custom integration conventions.

Use async APIs only.

Do not perform blocking I/O in the event loop.

Keep entities thin.

Prefer clear, typed, boring code over clever abstractions.

Use constants for Sony method names, services, setting types, and known output IDs.

Avoid broad `except Exception` unless the error is logged and intentionally converted into an integration-level failure.

## Pull Request / Change Checklist

Before completing a change, verify:

- [ ] No entity IDs changed accidentally.
- [ ] Config flow still works.
- [ ] Existing services still work.
- [ ] Tests pass.
- [ ] Mute payload remains `{"mute": "on/off"}`.
- [ ] Mute parsing does not treat `"off"` as truthy.
- [ ] Entities read from coordinator cache.
- [ ] Set actions update coordinator cache optimistically after success.
- [ ] No new per-entity polling was introduced.
- [ ] Diagnostics still work.
- [ ] README updated if user-facing behaviour changed.
- [ ] `manifest.json` version updated for release changes.

## Current Roadmap

Near-term priorities:

1. Reliable source selection.
2. Responsive optimistic UI updates.
3. Reduced coordinator traffic.
4. Better diagnostics and API timings.
5. Better Home Assistant device registry information.
6. Reconnection/availability polish.

Future priorities:

1. WebSocket notifications.
2. Zone 2/3 support.
3. Dynamic EQ controls.
4. User-configurable presets.
5. Broader Sony model testing.
