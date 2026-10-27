# ADR 0002: Instantes em UTC, datas de calendário sem fuso

- **Status:** Aceita
- **Data:** 2026-10-27

## Contexto

Datas são uma fonte comum de bugs silenciosos: horário gravado no fuso local do servidor, `datetime` sem fuso interpretado de jeitos diferentes em cada máquina, e datas que mudam de dia conforme quem consulta. O sistema pode ser consumido por clientes em fusos diferentes, como America/Sao_Paulo.

Há dois tipos de data no domínio, com naturezas diferentes:

- **Instante:** um ponto no tempo, com hora (`created_at`, quando o livro foi cadastrado).
- **Dia do calendário:** um dia, sem hora (a data de publicação).

## Decisão

- Todo instante é `datetime` com fuso, em UTC, no domínio e no banco. O nome leva o sufixo `_at`.
- `clock.utc_now()` é o único ponto do projeto que lê o relógio. Ninguém chama `datetime.now()` sem fuso.
- `clock.to_utc()` converte qualquer instante com fuso para UTC e recusa instante sem fuso (naive), inclusive o `tzinfo` que não informa offset, em vez de adivinhar de onde ele é.
- Dia do calendário é `date`, nunca `datetime`, e não passa por conversão de fuso.
- Clientes com outro relógio são atendidos na borda (entrada e saída da API), com um tradutor de fuso. Domínio e banco continuam em UTC.

## Alternativas consideradas

- **Data de publicação como instante UTC:** "10/03/2024 00:00 UTC" exibido em São Paulo vira 09/03 às 21h, e o livro muda de dia conforme quem consulta.
- **Horário local do servidor:** muda se o servidor mudar de região, e horário de verão gera horas repetidas ou inexistentes.

## Consequências

- O SQLite não tem tipo de data; instantes serão gravados em ISO 8601 com `+00:00` explícito. O adaptador padrão de `datetime` do `sqlite3` está deprecado desde o Python 3.12 e grava sem fuso, então não deve ser usado.
- Ao introduzir `ZoneInfo` (no tradutor de fuso), o Windows exige o pacote `tzdata`.
- "Que dia é hoje" depende do fuso; quem precisa do dia atual decide qual fuso vale (ver [ADR 0005](0005-publication-date-como-fonte-unica.md)).
