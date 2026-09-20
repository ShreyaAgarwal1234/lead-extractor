---
title: Business Card Lead Extractor
emoji: 📇
colorFrom: blue
colorTo: indigo
sdk: gradio
python_version: "3.11"
app_file: app.py
pinned: false
---

# Business Card Lead Extractor

Upload many business card photos at once. A **free, open-source Qwen vision-language model**
(`Qwen/Qwen2-VL-2B-Instruct`, Apache-2.0) reads every card and builds a structured lead list:

`First Name · Last Name · Position / Job Title · Company · Location · Phone Number · Email Address`

The leads are shown in the app and can be downloaded as a formatted Excel file.
No paid API is used anywhere: the model runs inside the app itself.

**Live URL:** `https://<username>-<space-name>.hf.space` *(fill in after deploying)*

## Project structure

```
bizcard-leads/
├── app.py                  # entry point: loads the model once, starts the web app
├── bizcard/
│   ├── config.py           # all settings, overridable via environment variables
│   ├── prompts.py          # the extraction prompt
│   ├── vlm.py              # Qwen model wrapper (GPU if available, else CPU)
│   ├── parsing.py          # model text -> validated, cleaned Lead
│   ├── schema.py           # Lead record + column names
│   ├── pipeline.py         # batch flow: image -> cache -> model -> parse -> table
│   ├── export.py           # Excel writer
│   └── ui.py               # Gradio interface (presentation only)
├── tests/                  # 42 unit tests, run without a GPU or the model
├── scripts/make_sample_cards.py   # creates fictional test cards in samples/
├── samples/                # 5 ready-made sample cards
├── requirements.txt
└── requirements-dev.txt
```

Data flow:

```
Browser -> Gradio UI -> pipeline -> prepare image (rotate, resize)
        -> Qwen2-VL (CPU/GPU) -> extract_json -> validate/clean -> Lead
        -> table in UI  +  leads_<timestamp>.xlsx
```

## Run locally

Requirements: Python 3.10+, about 10 GB free disk (model download, one time) and
**16 GB RAM recommended** for CPU use.

```bash
python -m venv venv
venv\Scripts\activate            # Windows      (Mac/Linux: source venv/bin/activate)
pip install -r requirements.txt
python app.py                    # open http://127.0.0.1:7860
```

The first start downloads the model (~4.5 GB). Try the cards in `samples/`.

Run the tests (no model needed): `pip install -r requirements-dev.txt && pytest`

## Deploy (free): Hugging Face Spaces

1. Create a Space: SDK **Gradio**, hardware **CPU basic (free, 16 GB RAM)**, visibility Public.
2. Upload / push everything in this folder (keep the YAML block at the top of this README).
3. Wait for the build (first start downloads the model). The app is then live at the Space URL.

## Configuration (environment variables)

| Variable | Default | Meaning |
|---|---|---|
| `MODEL_ID` | `Qwen/Qwen2-VL-2B-Instruct` | Any Qwen VL checkpoint supported by transformers. Check each model's license and RAM needs. |
| `DTYPE` | `auto` | `auto` (fp16 GPU / bf16 CPU), `float32`, `bfloat16`, `float16`. Try `float32` if CPU inference is very slow (needs ~9 GB RAM). |
| `MAX_FILES` | `20` | Max images per batch. |
| `MAX_PIXELS` | `401408` (512·28·28) | Visual-token budget per image. Lower = faster and less RAM, higher = more accurate on small text. |
| `MAX_IMAGE_SIDE` | `1024` | Longest image side in pixels before the model sees it. |
| `MAX_NEW_TOKENS` | `200` | Cap on generated tokens per card. |
| `CACHE_SIZE` | `200` | Number of card results remembered. |

## Engineering decisions

| Decision | Reasoning |
|---|---|
| **Qwen2-VL-2B-Instruct** | Smallest Qwen VLM with solid OCR. About 4.5 GB in bf16, so it fits free 16 GB CPU environments. Fully free, no API key. |
| **Free Hugging Face Space instead of the AWS free tier** | AWS free tier machines (t2/t3.micro) have 1 GB RAM, which cannot hold a VLM. The code is environment-agnostic: it detects a GPU automatically, so the same app runs on an EC2 GPU instance (e.g. g4dn.xlarge) with `python app.py` and `GRADIO_SERVER_NAME=0.0.0.0`. |
| **Model loaded once at startup** | Loading takes far longer than one inference; per-request loading would make batches unusable. |
| **Image preprocessing** | EXIF rotation fix (phone photos), RGB conversion, and downscaling. Visual tokens dominate CPU latency, so `max_pixels` is the main speed knob. |
| **Greedy decoding + token cap** | Deterministic output and a hard upper bound on time per card. |
| **Forgiving parser, strict output** | Accepts markdown fences, chatter and trailing commas; rejects malformed emails, implausible phone numbers and "N/A"-style values. Hallucinated emails are dropped instead of exported. |
| **Per-card error isolation** | A corrupt image or bad model answer is reported by filename and never stops the batch. |
| **Result cache (SHA-256 of file bytes)** | The same card uploaded twice is answered instantly without running the model. |
| **De-duplication by email** | Two photos of the same person produce one lead. |
| **Streaming UI** | The table and an ETA update after every card, which matters when each card takes many seconds. |
| **Queue with concurrency 1** | Two simultaneous model runs would double memory use and slow both down. |
| **Excel formula-injection guard** | Text read from a card that starts with `=` is stored as text, never as a formula. |
| **Model-free core** | `pipeline`, `parsing`, `export`, `ui` do not import torch; tests use a fake extractor. |

## Limitations

- CPU inference is slow (expect tens of seconds per card on 2 vCPUs); free Spaces sleep after inactivity.
- A 2B model can misread stylised fonts, tiny or blurry text, or heavily rotated cards.
  `Location` is inferred from the printed address and may be empty or approximate.
- Cards are processed one at a time.

## What I would do next (production)

- GPU instance with **vLLM** for batched inference; a job queue (SQS/Celery) with a worker, so uploads return immediately.
- A larger model, or a re-try with higher resolution for cards with missing fields.
- Editable results table before export, authentication, HTTPS, metrics and logging.
- Evaluate accuracy on a labelled set of real cards (field-level precision/recall).
