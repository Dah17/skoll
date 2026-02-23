import typing as t
from json import load
from skoll.domain import Locale


class I18N:

    base_path: str
    translations: dict[str, dict[str, str]]

    def __init__(self, base_path: str):

        self.translations = {}
        self.base_path = base_path

    def translate(self, key: str, locale: Locale, vars: dict[str, t.Any] | None = None) -> str:
        vars = vars or {}
        name = f"{locale.value.lower().replace('-', '_')}.json"

        if locale.value not in self.translations:
            with open(f"{self.base_path}/{name}", "r") as f:
                self.translations[locale.value] = load(f)

        text = self.translations[locale.value].get(key, f"Translation of <<{key}>> not found for <<{locale.value}>>")
        for k, v in vars.items():
            text = text.replace(f"<<{k}>>", str(v))
        return text
