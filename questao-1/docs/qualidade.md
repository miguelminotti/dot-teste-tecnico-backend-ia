# Qualidade da questão 1: testes e bugs

Como a suíte é pensada, o que ficou de fora e o registro dos bugs encontrados. Para rodar: `uv run pytest`, na pasta da questão.

## Política da suíte

- Cada teste protege uma regra de negócio ou um caso de borda conhecido, e um comentário dentro dele diz qual estrago evita. Meta de cobertura de linhas ficou de fora, porque incentiva teste que executa código sem verificar regra.
- Um teste só vale se fica vermelho quando sua regra é quebrada: cada regra foi quebrada à mão, uma por vez, e a suíte falhou em todas.
- Todo bug vira teste: primeiro um teste que o reproduz e falha, depois a correção.
- Infraestrutura e API rodam contra SQLite real, sem fake; a API sobe com `create_app` e o `TestClient`, que executa o lifespan como na subida real.

## Deixado de fora

- **Concorrência no rate limiter.** O teste com 64 threads disputando o mesmo contador passou com e sem o lock nas 10 rodadas: com o GIL do CPython, a corrida entre ler e gravar o contador quase nunca acontece num trecho tão curto. Um teste que não falha com a regra quebrada não protege nada, então saiu. O lock continua no código, porque a corrida existe.
- **409 pela API.** O `id` é gerado no domínio, então nenhum corpo de requisição produz um livro duplicado, e o 409 fica fora do contrato. O caso está coberto no repositório (`BookAlreadyExistsError`).
- **Teste de N+1.** A busca é uma consulta só, e a reidratação do `Book` não consulta o banco; com uma tabela e nenhuma relação, não existe N+1 possível. O teste entra junto com a primeira relação (autor como tabela própria, por exemplo), contando as consultas com `connection.set_trace_callback`.

## Bugs registrados

Cada bug tem um teste que o reproduziu antes da correção.

### 1. Texto só com caractere invisível era aceito

- **Bug:** título, autor ou resumo só com espaço de largura zero (U+200B) ou BOM (U+FEFF) passava pela validação, e o livro entrava com título invisível. Com o caractere nas pontas, "Machado de Assis" e "Machado de Assis" + U+200B viravam autores diferentes na busca.
- **Como apareceu:** escrevendo a suíte do domínio. O `str.strip()` só remove o que o Python considera espaço, e esses caracteres são da categoria Unicode "Cf" (formatação). Chegam colados de sites, PDFs e planilhas.
- **Testes que o protegem:** `test_rejects_blank_required_text` (casos `largura-zero`, `bom` e `misturado`) e `test_strips_invisible_characters_from_the_edges`.
- **Correção:** `_strip_invisible`, em `book.py`, remove espaços e caracteres "Cf" só das pontas. No meio do texto eles ficam, porque lá compõem emojis e a escrita de idiomas como persa e hindi. `test_keeps_invisible_characters_inside_the_text` impede que a correção vá longe demais.

Os bugs 2 a 7 foram encontrados na revisão final da questão, por um revisor independente. As limitações de menor impacto que a mesma revisão apontou ficaram registradas nas ADRs [0004](adr/0004-persistencia-sqlite3-com-repositorio-unico.md) e [0005](adr/0005-busca-sem-caixa-e-sem-acento.md), sem correção.

### 2. A correção do bug 1 era incompleta

- **Bug:** título só com caractere de controle (NUL), acento solto, braille em branco ou preenchedor hangul continuava sendo aceito: nenhum deles é espaço nem "Cf".
- **Testes que o protegem:** `test_rejects_text_without_any_letter_or_digit` e `test_keeps_real_text_and_strips_invisible_edges`.
- **Correção:** em vez de listar o que é invisível, o texto precisa ter pelo menos uma letra ou um número (categorias Unicode "L" e "N"). Os preenchedores hangul, que o Unicode classifica como letra, são tratados à parte, e caracteres de controle também saem das pontas.

### 3. `offset` grande derrubava a busca com 500

- **Bug:** `GET /books?offset=100000000000000000000` estourava o inteiro do sqlite3 (`OverflowError`) e respondia 500.
- **Teste:** `test_search_rejects_offset_beyond_the_ceiling`.
- **Correção:** teto de 1 milhão no `offset`.

### 4. Configuração inválida só aparecia com a API no ar

- **Bug:** `LIBRARY_RATE_LIMIT_WINDOW_SECONDS=0` fazia toda requisição dar 500 (divisão por zero), `LIBRARY_RATE_LIMIT_REQUESTS=0` bloqueava todo mundo com 429, e um fuso inválido derrubava a subida com um traceback sem o nome da variável.
- **Testes:** `test_settings.py`.
- **Correção:** o `Settings` valida os valores na construção, e o `from_env` nomeia a variável no erro.

### 5. O 422 tinha dois formatos, e o contrato anunciava um 409 inalcançável

- **Bug:** título vazio voltava como lista de erros (pydantic) e título só com espaços como texto (domínio). O OpenAPI do cadastro trazia o 422 sem schema e um 409 que nenhuma requisição produz.
- **Testes:** `test_validation_errors_have_one_shape_and_point_to_the_field` e `test_openapi_documents_only_the_errors_the_api_can_return`.
- **Correção:** o `DomainError` carrega o campo violado, e o handler devolve o mesmo formato do pydantic. O 409 continua como defesa, fora do contrato.

### 6. A virada da janela do rate limiter podia zerar os contadores mais de uma vez

- **Bug:** o relógio era lido fora do lock. Uma requisição atrasada da janela anterior que entrasse no lock depois de outra da janela nova fazia a janela "voltar" e zerava os contadores, e a requisição seguinte zerava de novo.
- **Teste:** `test_late_request_from_the_previous_window_does_not_reset_the_counters`, com um relógio que anda para trás para simular a ordem de chegada.
- **Correção:** o relógio é lido dentro do lock, e a janela só avança.

### 7. Espaços repetidos escondiam o livro na busca

- **Bug:** "dom  casmurro", com dois espaços (comum ao digitar ou colar), não achava "Dom Casmurro", e um título cadastrado com espaço duplo ou tab só era achado por quem digitasse o mesmo espaçamento.
- **Teste:** `test_search_ignores_repeated_whitespace`, nos dois sentidos (espaço duplo na busca e no título) e com tab.
- **Correção:** a normalização da busca reduz qualquer sequência de espaços, tabs e quebras de linha a um espaço só, tanto no texto gravado quanto no buscado.

Os bugs 8 e 9 foram encontrados numa segunda revisão independente, depois da entrega das três questões.

### 8. Cadastros falhavam com 500 sob concorrência

- **Bug:** com 64 clientes buscando e cadastrando ao mesmo tempo, de 2 a 13 de 500 cadastros respondiam 500 "database is locked". No journal padrão do SQLite, quem grava espera as leituras abertas terminarem e desiste depois do timeout de 5 s.
- **Teste:** `test_add_commits_while_another_connection_is_reading`, com uma conexão segurando uma leitura enquanto outra grava.
- **Correção:** as conexões abrem o banco no modo WAL, em que leitura e escrita não se bloqueiam. O mesmo teste de carga, 1.000 requisições de 64 clientes, passou sem nenhum erro.

### 9. Parâmetro de busca com nome errado devolvia o acervo inteiro

- **Bug:** `GET /books?autor=machado` (ou `?q=`) ignorava o parâmetro e respondia 200 com o acervo inteiro, como se a busca tivesse funcionado. O corpo do cadastro já recusava campo desconhecido.
- **Teste:** `test_search_rejects_unknown_parameters`.
- **Correção:** a busca recusa parâmetro desconhecido com 422, no mesmo formato dos outros erros de validação.
