# ADR 0006: Testes protegem regras de negócio; todo bug vira teste

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

Suíte de teste que só cobre linhas dá falsa segurança: passa verde enquanto a regra que importa está quebrada. Os comportamentos que mais custam quando quebram são os de negócio: livro que some da busca, lançamento que aparece antes da hora, horário gravado com três horas de diferença.

## Decisão

- Cada teste protege uma regra de negócio ou um caso de borda conhecido, e um comentário dentro dele diz qual estrago ele evita.
- Não se testa a mecânica da linguagem ou da biblioteca (imutabilidade da dataclass, `repr`), a não ser que ela sustente uma regra.
- Todo bug vira teste: primeiro um teste que reproduz o bug e falha, depois a correção. O teste fica na suíte, e o bug é registrado no README da questão (o que era, como apareceu, testes que o protegem, correção).
- Um teste só vale se fica vermelho quando sua regra é quebrada. Ao escrever testes para uma regra, ela é quebrada de propósito para confirmar que a suíte falha.
- Fusos nos testes usam offset fixo (`timezone(timedelta(hours=-3))`), não `ZoneInfo`: o que está em teste é a conversão, não a base de fusos do sistema operacional.
- Helpers de teste ficam no arquivo que os usa; vão para o `conftest.py`, como fixture, quando um segundo arquivo precisar deles.

## Alternativas consideradas

- **Meta de cobertura de linhas:** incentiva testes que executam código sem verificar regra.
- **Ferramenta de teste de mutação (mutmut, por exemplo):** automatiza a checagem de "regra quebrada, teste vermelho", mas é peso demais para o tamanho atual. As mutações foram feitas à mão.

## Consequências

- A suíte é pequena e cada teste tem motivo para existir.
- Caracteres invisíveis nos testes são escritos como sequências de escape (`"\u200b"`), nunca literais, para quem lê o código ver o que está sendo testado.
