# Newsletter diária

Site pessoal para ficar informado de notícias — https://gpecine.github.io/Newslatter/

- `index.html` — edição mais recente (troca todo dia).
- `edicoes/AAAA-MM-DD.html` — cada edição publicada, guardada sem alterações.
- `edicoes/index.html` — página com todas as edições anteriores.
- `dados/AAAA-MM-DD.json` — as notícias de cada edição em formato de dados (título, linha fina, resumo, editoria, fonte e link).
- `dados/noticias.csv` — todas as notícias de todas as edições numa tabela só, para checagem de fatos (abre no Excel ou Google Sheets).
- `scripts/arquivar.py` — arquiva uma edição nova: `python3 scripts/arquivar.py edicao.html AAAA-MM-DD`.
