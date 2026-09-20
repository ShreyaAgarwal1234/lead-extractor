"""Gradio web interface. Contains no model or parsing logic, only presentation."""
from __future__ import annotations

from pathlib import Path

import gradio as gr
import pandas as pd

from .config import Settings
from .export import write_excel
from .pipeline import LeadPipeline, LeadTable, Progress, build_lead_table
from .schema import LEAD_COLUMNS

TITLE = "Business Card Lead Extractor"
DESCRIPTION = (
    "Upload several business card photos at once. A Qwen vision-language model reads each "
    "card and builds a structured lead list that you can download as Excel.  \n"
    "_Tip: sharp, well-lit, upright photos give the best results._"
)


def _format_eta(seconds: float | None) -> str:
    if seconds is None:
        return ""
    minutes, secs = divmod(int(round(seconds)), 60)
    return f" · about {minutes} min {secs} s left" if minutes else f" · about {secs} s left"


def _progress_text(progress: Progress) -> str:
    return f"⏳ Processed **{progress.done} / {progress.total}** cards{_format_eta(progress.eta_seconds)}"


def _final_text(table: LeadTable, total: int) -> str:
    lines = [f"✅ Done. **{len(table.frame)} leads** extracted from {total} image(s)."]
    if table.duplicates:
        lines.append(f"{table.duplicates} duplicate card(s) skipped (same email).")
    if table.problems:
        lines.append("⚠️ Could not use:\n" + "\n".join(f"- {p}" for p in table.problems))
    return "\n\n".join(lines)


def make_handler(pipeline: LeadPipeline, settings: Settings):
    """Returns the generator function Gradio calls on 'Extract Leads'. Yielding after every
    card streams partial results to the browser (important on slow CPUs)."""

    def handle(files):
        if not files:
            yield pd.DataFrame(columns=LEAD_COLUMNS), "⚠️ Please upload at least one image.", None
            return

        # Gradio 4+ passes file paths (str); older versions pass objects with .name
        if isinstance(files, (str, Path)):
            files = [files]
        paths = [f if isinstance(f, str) else f.name for f in files]
        note = ""
        if len(paths) > settings.max_files:
            note = f"  \nOnly the first {settings.max_files} of {len(paths)} images are processed."

        last = None
        for last in pipeline.iter_process(paths):
            yield build_lead_table(last.results).frame, _progress_text(last) + note, None

        table = build_lead_table(last.results)
        excel_path = write_excel(table.frame) if not table.frame.empty else None
        yield table.frame, _final_text(table, last.total) + note, excel_path

    return handle


def build_demo(pipeline: LeadPipeline, settings: Settings) -> gr.Blocks:
    css = """
    :root { --ink: #18302b; --muted: #62736e; --mint: #dff4e9; --line: #d7e5df; }
    .gradio-container { max-width: 1180px !important; background: #f7faf8; }
    .hero { padding: 34px 38px 28px; border-radius: 22px; background: linear-gradient(120deg, #153d36, #26725d); color: white; box-shadow: 0 14px 32px #164b3b20; }
    .hero h1 { margin: 0 0 8px; font-size: 2.2rem; letter-spacing: -0.02em; }
    .hero p { margin: 0; max-width: 680px; color: #e0f3eb; font-size: 1.02rem; }
    .section-title { color: var(--ink); font-size: 1.1rem; font-weight: 700; margin: 2px 0 8px; }
    .upload-box { border: 1.5px dashed #7bb59e !important; background: var(--mint) !important; min-height: 165px; }
    .hint { color: var(--muted); font-size: 0.9rem; margin-top: 8px; }
    .status-box { min-height: 48px; padding: 12px 16px; border: 1px solid var(--line); border-radius: 12px; background: white; }
    .lead-table { min-height: 360px; }
    .run-button { min-height: 48px; font-weight: 700; }
    footer { display: none !important; }
    """
    with gr.Blocks(title=TITLE, theme=gr.themes.Soft(primary_hue="emerald"), css=css) as demo:
        gr.HTML(
            '<header class="hero"><h1>Turn cards into contacts.</h1>'
            '<p>Upload a batch of business card photos and get a clean, downloadable lead list in minutes.</p></header>'
        )
        gr.Markdown("### 1. Add your business cards", elem_classes="section-title")
        uploader = gr.File(
            label=f"Drop up to {settings.max_files} images here, or browse",
            file_count="multiple",
            file_types=["image"],
            type="filepath",
            elem_classes="upload-box",
        )
        gr.Markdown(
            "JPG, PNG, or WEBP · Upload several images together · Sharp, upright photos work best",
            elem_classes="hint",
        )
        with gr.Row():
            run_button = gr.Button("Extract leads", variant="primary", elem_classes="run-button")
            clear_button = gr.ClearButton(value="Clear", variant="secondary")
        gr.Markdown("### 2. Review and download", elem_classes="section-title")
        status = gr.Markdown("Your extracted leads will appear here.", elem_classes="status-box")
        table = gr.Dataframe(
            headers=LEAD_COLUMNS, label="Lead list", interactive=False, wrap=True,
            show_search="filter", elem_classes="lead-table",
        )
        excel = gr.File(label="Download Excel workbook", interactive=False)

        run_button.click(
            make_handler(pipeline, settings), inputs=uploader, outputs=[table, status, excel]
        )
        clear_button.add([uploader, table, status, excel])

    # One card at a time: two parallel model runs would double RAM use and slow both down.
    demo.queue(max_size=5, default_concurrency_limit=1)
    return demo
