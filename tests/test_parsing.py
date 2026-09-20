import pytest

from bizcard.parsing import build_lead, clean_email, clean_phone, clean_text, extract_json


class TestExtractJson:
    def test_plain_json(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_markdown_fence_and_chatter(self):
        raw = 'Sure! Here you go:\n```json\n{"first_name": "Asha"}\n```\nHope this helps.'
        assert extract_json(raw) == {"first_name": "Asha"}

    def test_trailing_comma_is_repaired(self):
        assert extract_json('{"a": "x", "b": "y",}') == {"a": "x", "b": "y"}

    @pytest.mark.parametrize("raw", ["no json here", "", "{broken", '{"a": }'])
    def test_garbage_raises_value_error(self, raw):
        with pytest.raises(ValueError):
            extract_json(raw)


class TestCleaners:
    @pytest.mark.parametrize("value", [None, "", "null", "N/A", "  none ", "-"])
    def test_nullish_becomes_empty(self, value):
        assert clean_text(value) == ""

    def test_whitespace_collapsed_and_list_joined(self):
        assert clean_text("  Sales \n  Manager ") == "Sales Manager"
        assert clean_text(["a", "b"]) == "a, b"

    def test_email_valid_lowercased(self):
        assert clean_email("Rahul@ABC.com") == "rahul@abc.com"
        assert clean_email("mailto:x@y.co.in") == "x@y.co.in"

    @pytest.mark.parametrize("value", ["rahul@abc", "not an email", "@abc.com", None])
    def test_email_invalid_rejected(self, value):
        assert clean_email(value) == ""

    def test_first_valid_email_wins(self):
        assert clean_email("bad, good@x.com; other@y.com") == "good@x.com"

    def test_phone_keeps_formatting_drops_labels(self):
        assert clean_phone("Tel: +91 98765 43210") == "+91 98765 43210"

    def test_multiple_phones(self):
        assert clean_phone("+91 98765 43210, 011-2345-6789") == "+91 98765 43210, 011-2345-6789"

    @pytest.mark.parametrize("value", ["123", "abc", None, "1" * 30])
    def test_phone_implausible_rejected(self, value):
        assert clean_phone(value) == ""


class TestBuildLead:
    def test_full_record(self):
        lead = build_lead(
            {
                "first_name": "Rahul", "last_name": "Sharma", "position": "Sales Manager",
                "company": "ABC Pvt Ltd", "location": "Delhi, India",
                "phone": "+91 98765 43210", "email": "Rahul@ABC.com",
            },
            "card.png",
        )
        assert lead.as_row() == [
            "Rahul", "Sharma", "Sales Manager", "ABC Pvt Ltd", "Delhi, India",
            "+91 98765 43210", "rahul@abc.com", "card.png",
        ]

    def test_full_name_in_first_name_is_split(self):
        lead = build_lead({"first_name": "Rahul Kumar Sharma", "last_name": None}, "c.png")
        assert (lead.first_name, lead.last_name) == ("Rahul Kumar", "Sharma")

    def test_honorific_removed_and_uppercase_fixed(self):
        lead = build_lead({"first_name": "DR. PRIYA", "last_name": "NAIR"}, "c.png")
        assert (lead.first_name, lead.last_name) == ("Priya", "Nair")

    def test_missing_keys_do_not_crash(self):
        lead = build_lead({}, "c.png")
        assert not lead.has_contact_info()
