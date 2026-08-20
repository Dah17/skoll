import typing as t
from json import load
from skoll.domain import Locale

__all__ = ["I18n"]


class I18n:

    base_path: str
    fallback: Locale
    translations: dict[str, dict[str, str]]

    def __init__(self, base_path: str, fallback: Locale | None = None):

        self.translations = {}
        self.base_path = base_path
        self.fallback = fallback or Locale(value="en-US")

    def translate(self, key: str, locale: Locale, vars: dict[str, t.Any] | None = None) -> str:
        vars = vars or {}
        if locale.value not in self.translations:
            self.translations[locale.value] = self._get_translations(locale)

        text = self.translations[locale.value].get(key, f"Translation of <<{key}>> not found for <<{locale.value}>>")
        for k, v in vars.items():
            text = text.replace(f"<<{k}>>", str(v))
        return text

    def _get_translations(self, locale: Locale) -> dict[str, str]:
        translations = self._load_translations(locale)
        if translations is not None:
            return translations
        if locale.value == self.fallback.value:
            return {}
        return self._load_translations(self.fallback) or {}

    def _load_translations(self, locale: Locale) -> dict[str, str] | None:
        name = f"{locale.value.lower().replace('-', '_')}.json"
        try:
            with open(f"{self.base_path}/{name}", "r", encoding="utf-8") as f:
                return load(f)
        except FileNotFoundError:
            return None
