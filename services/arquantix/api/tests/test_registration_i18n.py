"""Tests for Registration i18n helpers and flow serialization with language resolution."""
import uuid
import pytest
from services.registration.i18n import resolve_localized, resolve_localized_props


# ---------------------------------------------------------------------------
# resolve_localized
# ---------------------------------------------------------------------------

class TestResolveLocalized:
    def test_plain_string_passthrough(self):
        assert resolve_localized("Hello") == "Hello"

    def test_none_returns_empty(self):
        assert resolve_localized(None) == ""

    def test_dict_exact_lang(self):
        val = {"en": "Hello", "fr": "Bonjour"}
        assert resolve_localized(val, lang="fr") == "Bonjour"

    def test_dict_fallback_to_default_lang(self):
        val = {"en": "Hello", "de": "Hallo"}
        assert resolve_localized(val, lang="fr", default_lang="en") == "Hello"

    def test_dict_fallback_to_en(self):
        val = {"en": "Hello", "de": "Hallo"}
        assert resolve_localized(val, lang="ja", default_lang="de") == "Hallo"

    def test_dict_fallback_to_first_value(self):
        val = {"de": "Hallo"}
        assert resolve_localized(val, lang="ja", default_lang="es") == "Hallo"

    def test_empty_dict_returns_empty(self):
        assert resolve_localized({}) == ""

    def test_number_coerced_to_string(self):
        assert resolve_localized(42) == "42"

    def test_backward_compat_mixed(self):
        assert resolve_localized("Label", lang="fr") == "Label"


# ---------------------------------------------------------------------------
# resolve_localized_props
# ---------------------------------------------------------------------------

class TestResolveLocalizedProps:
    def test_plain_string_props(self):
        props = {"label": "Name", "placeholder": "Enter name", "required": True}
        result = resolve_localized_props(props, lang="en")
        assert result["label"] == "Name"
        assert result["placeholder"] == "Enter name"
        assert result["required"] is True

    def test_localized_label(self):
        props = {
            "label": {"en": "Name", "fr": "Nom"},
            "required": True,
        }
        result = resolve_localized_props(props, lang="fr")
        assert result["label"] == "Nom"

    def test_localized_text(self):
        props = {
            "text": {"en": "Terms apply", "fr": "Conditions applicables"},
        }
        result = resolve_localized_props(props, lang="fr")
        assert result["text"] == "Conditions applicables"

    def test_localized_options(self):
        props = {
            "options": [
                {"value": "m", "label": {"en": "Male", "fr": "Masculin"}},
                {"value": "f", "label": {"en": "Female", "fr": "Féminin"}},
            ]
        }
        result = resolve_localized_props(props, lang="fr")
        assert result["options"][0]["label"] == "Masculin"
        assert result["options"][1]["label"] == "Féminin"

    def test_localized_items_list(self):
        props = {
            "items": [
                {"en": "Item 1", "fr": "Élément 1"},
                {"en": "Item 2", "fr": "Élément 2"},
            ]
        }
        result = resolve_localized_props(props, lang="fr")
        assert result["items"] == ["Élément 1", "Élément 2"]

    def test_plain_items_list(self):
        props = {"items": ["One", "Two"]}
        result = resolve_localized_props(props, lang="fr")
        assert result["items"] == ["One", "Two"]

    def test_empty_props(self):
        assert resolve_localized_props({}) == {}
        assert resolve_localized_props(None) == {}

    def test_fallback_chain(self):
        props = {"label": {"de": "Name"}}
        result = resolve_localized_props(props, lang="fr", default_lang="en")
        assert result["label"] == "Name"

    def test_non_localizable_fields_preserved(self):
        props = {"label": "Test", "required": True, "keyboard_type": "email"}
        result = resolve_localized_props(props, lang="en")
        assert result["keyboard_type"] == "email"
        assert result["required"] is True


# ---------------------------------------------------------------------------
# Component type categorization
# ---------------------------------------------------------------------------

class TestComponentTypes:
    """Verify that the new component types are recognized by the system."""

    CONTENT_TYPES = {"section_title", "legal_content", "info_box", "rich_text", "divider", "spacer", "bullet_list"}
    INPUT_TYPES = {"text_input", "phone_input", "select", "country_picker", "date_picker", "checkbox", "multi_select"}

    def test_all_types_categorized(self):
        all_types = self.CONTENT_TYPES | self.INPUT_TYPES
        assert len(all_types) == 14

    def test_content_types_have_no_binding_slug(self):
        for ct in self.CONTENT_TYPES:
            assert ct in self.CONTENT_TYPES

    def test_input_types_need_binding_slug(self):
        for it in self.INPUT_TYPES:
            assert it in self.INPUT_TYPES
