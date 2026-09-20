import gradio as gr

from bizcard.config import load_settings
from bizcard.pipeline import LeadPipeline
from bizcard.ui import build_demo, make_handler


class FakeExtractor:
    def generate(self, image):
        return '{"first_name": "Asha", "last_name": "Rao", "company": "Acme", "email": "asha@acme.com"}'


def test_demo_builds():
    demo = build_demo(LeadPipeline(FakeExtractor(), load_settings()), load_settings())
    assert isinstance(demo, gr.Blocks)


def test_handler_streams_and_produces_excel(tmp_path):
    from PIL import Image

    settings = load_settings()
    img = tmp_path / "c.png"
    Image.new("RGB", (300, 200), "white").save(img)

    outputs = list(make_handler(LeadPipeline(FakeExtractor(), settings), settings)([str(img)]))
    frame, status, excel = outputs[-1]
    assert len(frame) == 1 and "Done" in status and excel.endswith(".xlsx")


def test_handler_without_files():
    settings = load_settings()
    frame, status, excel = next(make_handler(LeadPipeline(FakeExtractor(), settings), settings)([]))
    assert frame.empty and excel is None and "upload" in status.lower()
