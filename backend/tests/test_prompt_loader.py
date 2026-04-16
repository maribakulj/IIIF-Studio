"""
Tests pour prompt_loader.py — chargement, rendu, et détection de variables non résolues.
"""
import pytest

from app.services.ai.prompt_loader import load_and_render_prompt


@pytest.fixture()
def template_file(tmp_path):
    """Crée un fichier template temporaire."""
    def _create(content: str, name: str = "test_prompt.txt"):
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        return path
    return _create


class TestLoadAndRenderPrompt:
    def test_simple_substitution(self, template_file):
        path = template_file("Analysez ce {{profile_label}} en {{script_type}}.")
        result = load_and_render_prompt(path, {
            "profile_label": "manuscrit enluminé",
            "script_type": "caroline",
        })
        assert result == "Analysez ce manuscrit enluminé en caroline."

    def test_multiple_occurrences(self, template_file):
        path = template_file("{{lang}} et encore {{lang}}")
        result = load_and_render_prompt(path, {"lang": "latin"})
        assert result == "latin et encore latin"

    def test_unused_context_keys_ignored(self, template_file):
        path = template_file("Hello {{name}}")
        result = load_and_render_prompt(path, {"name": "World", "extra": "unused"})
        assert result == "Hello World"

    def test_unresolved_variable_raises(self, template_file):
        path = template_file("{{resolved}} but {{unresolved}} remains")
        with pytest.raises(ValueError, match="Variables non résolues"):
            load_and_render_prompt(path, {"resolved": "ok"})

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Template introuvable"):
            load_and_render_prompt(tmp_path / "nonexistent.txt", {})

    def test_empty_template(self, template_file):
        path = template_file("")
        result = load_and_render_prompt(path, {"key": "value"})
        assert result == ""

    def test_no_variables_in_template(self, template_file):
        path = template_file("Just plain text, no variables.")
        result = load_and_render_prompt(path, {})
        assert result == "Just plain text, no variables."

    def test_path_as_string(self, template_file):
        path = template_file("{{x}}")
        result = load_and_render_prompt(str(path), {"x": "replaced"})
        assert result == "replaced"
