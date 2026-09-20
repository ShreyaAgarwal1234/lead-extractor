"""Entry point.  Run locally with:  python app.py   (Hugging Face Spaces runs this file too)."""
import logging

from bizcard.config import load_settings
from bizcard.pipeline import LeadPipeline
from bizcard.ui import build_demo
from bizcard.vlm import QwenVLExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

settings = load_settings()
extractor = QwenVLExtractor(settings).load()  # load once at startup, not per request
demo = build_demo(LeadPipeline(extractor, settings), settings)

if __name__ == "__main__":
    demo.launch()
