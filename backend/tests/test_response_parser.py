"""
Tests pour response_parser.py — extraction JSON, correction VLM, parsing tolérant.
"""
import pytest

from app.services.ai.response_parser import (
    ParseError,
    _extract_json_object,
    _fix_common_json_issues,
    _try_parse_json,
    parse_ai_response,
)


# ── _extract_json_object ─────────────────────────────────────────────────────

class TestExtractJsonObject:
    def test_simple_object(self):
        assert _extract_json_object('{"a": 1}') == '{"a": 1}'

    def test_text_before_json(self):
        result = _extract_json_object('Here is the JSON: {"a": 1}')
        assert result == '{"a": 1}'

    def test_text_after_json(self):
        result = _extract_json_object('{"a": 1} and more text')
        assert result == '{"a": 1}'

    def test_nested_braces(self):
        result = _extract_json_object('{"a": {"b": {"c": 1}}}')
        assert result == '{"a": {"b": {"c": 1}}}'

    def test_braces_inside_strings(self):
        result = _extract_json_object('{"text": "value with { and } inside"}')
        assert result == '{"text": "value with { and } inside"}'

    def test_escaped_quotes(self):
        result = _extract_json_object('{"text": "he said \\"hello\\""}')
        assert result == '{"text": "he said \\"hello\\""}'

    def test_no_json(self):
        result = _extract_json_object("no json here")
        assert result == "no json here"

    def test_unclosed_json(self):
        result = _extract_json_object('some text {"a": 1')
        assert result.startswith('{"a": 1')


# ── _fix_common_json_issues ──────────────────────────────────────────────────

class TestFixCommonJsonIssues:
    def test_trailing_comma_before_brace(self):
        assert _fix_common_json_issues('{"a": 1,}') == '{"a": 1}'

    def test_trailing_comma_before_bracket(self):
        assert _fix_common_json_issues('[1, 2,]') == '[1, 2]'

    def test_trailing_comma_with_whitespace(self):
        assert _fix_common_json_issues('{"a": 1 , }') == '{"a": 1 }'

    def test_no_issues(self):
        text = '{"a": 1, "b": 2}'
        assert _fix_common_json_issues(text) == text


# ── _try_parse_json ──────────────────────────────────────────────────────────

class TestTryParseJson:
    def test_valid_json(self):
        assert _try_parse_json('{"a": 1}') == {"a": 1}

    def test_json_with_trailing_comma(self):
        result = _try_parse_json('{"a": 1,}')
        assert result == {"a": 1}

    def test_invalid_json(self):
        assert _try_parse_json("not json at all") is None


# ── parse_ai_response ────────────────────────────────────────────────────────

class TestParseAiResponse:
    def test_clean_json(self):
        raw = '{"layout": {"regions": [{"id": "r1", "type": "text_block", "bbox": [10, 20, 100, 200], "confidence": 0.9}]}, "ocr": {"diplomatic_text": "hello", "confidence": 0.8}}'
        layout, ocr = parse_ai_response(raw)
        assert len(layout["regions"]) == 1
        assert layout["regions"][0]["id"] == "r1"
        assert ocr.diplomatic_text == "hello"

    def test_markdown_fenced_json(self):
        raw = '```json\n{"layout": {"regions": []}, "ocr": {"diplomatic_text": "test"}}\n```'
        layout, ocr = parse_ai_response(raw)
        assert layout["regions"] == []
        assert ocr.diplomatic_text == "test"

    def test_text_around_json(self):
        raw = 'Here is my analysis:\n{"layout": {"regions": []}, "ocr": {"diplomatic_text": "ok"}}\nHope this helps!'
        layout, ocr = parse_ai_response(raw)
        assert ocr.diplomatic_text == "ok"

    def test_invalid_region_skipped(self):
        raw = '{"layout": {"regions": [{"id": "r1", "type": "text_block", "bbox": [-1, 0, 100, 200], "confidence": 0.5}, {"id": "r2", "type": "miniature", "bbox": [10, 20, 100, 200], "confidence": 0.8}]}}'
        layout, ocr = parse_ai_response(raw)
        assert len(layout["regions"]) == 1
        assert layout["regions"][0]["id"] == "r2"

    def test_missing_ocr_returns_default(self):
        raw = '{"layout": {"regions": []}}'
        layout, ocr = parse_ai_response(raw)
        assert ocr.diplomatic_text == ""
        assert ocr.confidence == 0.0

    def test_not_json_raises_parse_error(self):
        with pytest.raises(ParseError):
            parse_ai_response("This is not JSON at all, no braces anywhere")

    def test_json_array_raises_parse_error(self):
        with pytest.raises(ParseError):
            parse_ai_response("[1, 2, 3]")

    def test_trailing_comma_tolerance(self):
        raw = '{"layout": {"regions": [],}, "ocr": {"diplomatic_text": "tolerant",}}'
        layout, ocr = parse_ai_response(raw)
        assert ocr.diplomatic_text == "tolerant"
