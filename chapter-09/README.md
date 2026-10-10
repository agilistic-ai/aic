# Chapter 9 — Media intake and review

This standalone application turns an image or short PDF plus a PCM WAV recording into a draft, preserves disagreements, and asks for review. It does not diagnose a fault or book an appointment.

Install with `uv sync --locked` using Python 3.12. Set `AIC_API_KEY` for the hosted media service. Run from this folder or provide `--config` for text-model settings. Media processing uses the hosted OpenAI adapter even when you select Ollama for the text stages. Obtain consent for the configured processing destination before invoking intake.

```sh
uv run media intake /path/to/label.png /path/to/note.wav --consent
uv run media intake /path/to/label.pdf /path/to/note.wav --consent --method joint
```

Inputs must be PNG/JPEG or an unencrypted PDF of one to five pages, plus 16-bit PCM WAV at 16–48 kHz, at most one minute. The application caps upload sizes and normalizes image/audio metadata. No microphone is activated. Supply a recording you are authorized to process. `--output` changes the working-data folder.

The command prints the saved draft path. Inspect it and review the source media:

```sh
uv run media show runs/media/RECORD_ID/draft-DRAFT_ID.json
uv run media review runs/media/RECORD_ID/draft-DRAFT_ID.json
```

Replace identifiers with the printed path. `review` is interactive: Enter keeps a proposed value, `?` makes it unknown, and approval requires a problem description plus explicit resolution of open questions. The reviewer name is a local audit label, not authentication. Asset paths are absolute so a later review can run from another directory. Moving a record requires deliberately updating its stored paths and repeating review.

For a separate review interface, `approve` accepts a complete fields JSON file, the exact digest printed by `show`, a reviewer label, and `--questions-resolved`:

```sh
uv run media approve DRAFT_PATH --fields confirmed-fields.json --digest SHA256_FROM_SHOW --reviewer Reader --questions-resolved
```

The fields file contains `item_model` (string or null), `problem` (nonempty string), and `preferred_time` (string or null). A changed draft or changed media invalidates approval. Original evidence is preserved; corrections are recorded separately.

Optional spoken confirmation uses only a reviewed intake:

```sh
uv run media speak REVIEWED_PATH --output runs/confirmation.wav
```

The same confirmation stays in `confirmation.txt` if speech generation fails. Playback is identified as AI-generated. The app produces a WAV file; playback belongs to the user's chosen media player.

`AIC_VISION_MODEL`, `AIC_TRANSCRIBE_MODEL`, and `AIC_SPEECH_MODEL` override the media model names. Defaults are recorded in the code. `AIC_MEDIA_BASE_URL` selects a compatible media endpoint; otherwise `AIC_OPENAI_BASE_URL` or the SDK's hosted default applies. Text configuration uses `config.toml` or `--config configs/ollama.toml`. Selecting local text does not make vision, transcription, or speech local.

The staged method saves the visual reading before transcription. If audio fails, `visual.json` remains beside `failure.json`. Each job keeps a manifest, reported usage where supplied, selected model settings, assets and stage results. Unknown usage remains unknown. Joint interpretation transcribes first, then reads the visual source and transcript together.

These working files contain personal content. This local CLI relies on filesystem ownership. Delete its record directory when no longer needed and manage original uploads separately; it does not claim to delete provider copies or supply a deployed access-control/retention service.

## Smoke verification

```sh
uv run python -m unittest discover -s tests -v
```

The suite installs and invokes the complete CLI, uses real Pillow/PDF/WAV parsing, and sends actual OpenAI/Ollama SDK requests to a local scripted HTTP service. It checks staged and joint intake, PDF extraction, conflicting model markings, stale review rejection, corrections, streamed speech output, and failed-stage preservation. The silence and generated label in tests are transport fixtures, not speech/vision accuracy evidence. Live hosted or local inference was not tested. See SMOKE_REPORT.md.

## Copyright, license, and disclaimer

Copyright (c) 2026, Agilistic AI LLC, All Rights Reserved

You may run, copy, modify, and redistribute these examples, including as part of commercial applications, under the [MIT License](LICENSE.txt). Keep the copyright and permission notices with copies or substantial portions. Agilistic AI LLC retains copyright; "All Rights Reserved" is subject to this license grant.

The materials come with **no warranty**. Use them at your own risk, review generated outputs and actions, and account for external service charges. Read the [full disclaimer](DISCLAIMER.md) for warranty and liability provisions. Third-party dependencies retain their own licenses and terms.
