import json

import pytest
from PIL import Image

from bizcard.config import load_settings
from bizcard.pipeline import LeadPipeline, build_lead_table


class FakeExtractor:
    """Stands in for the real model so tests need no GPU, no download, no torch."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.calls = 0

    def generate(self, image):
        self.calls += 1
        return self.answers.pop(0)


def card_json(**overrides):
    data = {"first_name": "Asha", "last_name": "Rao", "position": "CEO", "company": "Acme",
            "location": "Pune", "phone": "+91 98765 43210", "email": "asha@acme.com"}
    data.update(overrides)
    return json.dumps(data)


def make_image(path, color):
    Image.new("RGB", (400, 250), color).save(path)
    return str(path)


@pytest.fixture
def settings():
    return load_settings()


def run(pipeline, paths):
    last = None
    for last in pipeline.iter_process(paths):
        pass
    return last


def test_happy_path(tmp_path, settings):
    paths = [make_image(tmp_path / "a.png", "red"), make_image(tmp_path / "b.png", "blue")]
    extractor = FakeExtractor([card_json(), card_json(first_name="Ben", email="ben@acme.com")])
    progress = run(LeadPipeline(extractor, settings), paths)

    table = build_lead_table(progress.results)
    assert progress.done == progress.total == 2
    assert list(table.frame["First Name"]) == ["Asha", "Ben"]
    assert not table.problems


def test_bad_json_and_corrupt_image_do_not_stop_batch(tmp_path, settings):
    good = make_image(tmp_path / "good.png", "red")
    bad_json = make_image(tmp_path / "bad_json.png", "green")
    corrupt = tmp_path / "corrupt.png"
    corrupt.write_bytes(b"this is not an image")

    extractor = FakeExtractor(["I cannot read this card", card_json()])
    progress = run(LeadPipeline(extractor, settings), [bad_json, str(corrupt), good])
    table = build_lead_table(progress.results)

    assert len(table.frame) == 1
    assert len(table.problems) == 2
    assert any("bad_json.png" in p for p in table.problems)
    assert any("corrupt.png" in p for p in table.problems)


def test_same_image_is_served_from_cache(tmp_path, settings):
    first = make_image(tmp_path / "one.png", "red")
    copy = tmp_path / "copy.png"
    copy.write_bytes((tmp_path / "one.png").read_bytes())

    extractor = FakeExtractor([card_json()])  # only ONE model answer available
    progress = run(LeadPipeline(extractor, settings), [first, str(copy)])

    assert extractor.calls == 1
    assert [r.lead.source_file for r in progress.results] == ["one.png", "copy.png"]


def test_duplicate_email_is_dropped(tmp_path, settings):
    paths = [make_image(tmp_path / "a.png", "red"), make_image(tmp_path / "b.png", "blue")]
    extractor = FakeExtractor([card_json(), card_json(first_name="Asha2")])  # same email
    table = build_lead_table(run(LeadPipeline(extractor, settings), paths).results)
    assert len(table.frame) == 1
    assert table.duplicates == 1


def test_blank_card_is_reported_not_added(tmp_path, settings):
    path = make_image(tmp_path / "blank.png", "white")
    empty = json.dumps({k: None for k in ["first_name", "last_name", "position", "company",
                                          "location", "phone", "email"]})
    table = build_lead_table(run(LeadPipeline(FakeExtractor([empty]), settings), [path]).results)
    assert table.frame.empty
    assert "no contact details" in table.problems[0]


def test_max_files_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_FILES", "2")
    paths = [make_image(tmp_path / f"{i}.png", (i * 40, 0, 0)) for i in range(5)]
    answers = [card_json(email=f"p{i}@x.com") for i in range(5)]
    progress = run(LeadPipeline(FakeExtractor(answers), load_settings()), paths)
    assert progress.total == 2
