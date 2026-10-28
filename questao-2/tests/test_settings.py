import pytest

from chatbot.settings import Settings


@pytest.mark.parametrize(("value", "expected"), [("true", True), ("false", False), ("", True)])
def test_docs_search_flag_is_read(value: str, expected: bool) -> None:
    # Vazio é o padrão da ADR 0002: a busca ligada.
    settings = Settings.from_env({"OPENAI_API_KEY": "chave", "CHATBOT_DOCS_SEARCH": value})

    assert settings.docs_search is expected


def test_docs_search_flag_with_unknown_value_is_an_error() -> None:
    # Um "ture" lido como desligado faria o braço "com busca" do experimento rodar sem a busca, e a
    # comparação concluiria que a busca não muda nada.
    with pytest.raises(ValueError, match="CHATBOT_DOCS_SEARCH"):
        Settings.from_env({"OPENAI_API_KEY": "chave", "CHATBOT_DOCS_SEARCH": "ture"})
