"""API HTTP: as rotas falam só com a camada de aplicação.

`app.py` e `dependencies.py` são o ponto de montagem: os únicos módulos da API que conhecem a
infraestrutura (para ligar o `BookService` ao SQLite) e os erros do domínio (para traduzi-los em
respostas HTTP).
"""
