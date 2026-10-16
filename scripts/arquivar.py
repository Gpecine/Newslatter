#!/usr/bin/env python3
"""Arquiva uma edição da Newsletter diária no repositório.

Uso:  python3 scripts/arquivar.py CAMINHO_DA_EDICAO.html AAAA-MM-DD

O que faz:
  1. Copia a edição para edicoes/AAAA-MM-DD.html (versão que nunca mais muda).
  2. Publica a edição como index.html (a página principal do site).
  3. Extrai cada notícia para dados/AAAA-MM-DD.json.
  4. Reconstrói dados/noticias.csv com TODAS as notícias de todas as edições
     (abre no Excel / Google Sheets para checagem de fatos).
  5. Reconstrói edicoes/index.html, a página de arquivo com todas as edições.
"""
import csv, html, json, os, re, sys
from html.parser import HTMLParser

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EDITORIAS = {"games": "Games", "ia": "IA", "tec": "Tecnologia",
             "hw": "Hardware", "car": "Carros", "pol": "Política"}


class Extrator(HTMLParser):
    """Lê a manchete (.hero), os destaques (.dest) e os cards (.card)."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.noticias, self.destaques = [], []
        self.atual = None          # notícia sendo lida
        self.campo = None          # 'titulo' | 'fina' | 'txt' | 'src' | 'kick'
        self.profundidade = 0      # profundidade da tag que abriu a notícia
        self.pilha = 0
        self.na_dest = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = (a.get("class") or "").split()
        self.pilha += 1
        if tag == "section" and "dest" in cls:
            self.na_dest = True
        if self.na_dest and tag == "a" and a.get("href"):
            self.destaques.append({"link": a["href"], "titulo": ""})
            return
        if self.na_dest and tag == "span" and "dt" in cls:
            self.campo = "dest"
            return
        editoria = next((c[3:] for c in cls if c.startswith("ed-")), None)
        if self.atual is None and ("hero" in cls or "card" in cls) and editoria:
            self.atual = {"tipo": "manchete" if "hero" in cls else "noticia",
                          "editoria": EDITORIAS.get(editoria, editoria),
                          "id": a.get("id", ""), "chapeu": "", "titulo": "",
                          "linha_fina": "", "texto": "", "fonte": "", "link": ""}
            self.profundidade = self.pilha
            return
        if self.atual is None:
            return
        if tag in ("h1", "h3"):
            self.campo = "titulo"
        elif tag == "a" and self.campo == "titulo" and not self.atual["link"]:
            self.atual["link"] = a.get("href", "")
        elif tag == "p" and "fina" in cls:
            self.campo = "linha_fina"
        elif tag == "p" and "txt" in cls:
            self.campo = "texto"
        elif tag == "span" and "src" in cls:
            self.campo = "fonte"
        elif tag == "span" and "kick" in cls:
            self.campo = "chapeu"

    def handle_endtag(self, tag):
        if tag == "section" and self.na_dest:
            self.na_dest = False
        if self.campo == "dest" and tag == "span":
            self.campo = None
        elif self.campo and tag in ("h1", "h3", "p", "span") and self.campo != "dest":
            self.campo = None
        if self.atual is not None and self.pilha == self.profundidade:
            self.noticias.append({k: re.sub(r"\s+", " ", v).strip() if isinstance(v, str) else v
                                  for k, v in self.atual.items()})
            self.atual = None
        self.pilha -= 1

    def handle_data(self, dado):
        if self.campo == "dest" and self.destaques:
            self.destaques[-1]["titulo"] += dado
        elif self.atual is not None and self.campo:
            self.atual[self.campo] += dado


def ler(caminho):
    with open(caminho, encoding="utf-8") as f:
        return f.read()


def gravar(caminho, texto):
    os.makedirs(os.path.dirname(caminho), exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        f.write(texto)


def extrair(pagina, data):
    ex = Extrator()
    ex.feed(pagina)
    titulo = re.search(r"<title>(.*?)</title>", pagina, re.S)
    data_ext = re.search(r'<p class="date">(.*?)</p>', pagina, re.S)
    return {
        "data": data,
        "titulo": html.unescape(titulo.group(1)).strip() if titulo else "",
        "data_por_extenso": html.unescape(data_ext.group(1)).strip() if data_ext else "",
        "pagina": f"edicoes/{data}.html",
        "destaques": [{k: re.sub(r"\s+", " ", v).strip() for k, v in d.items()} for d in ex.destaques],
        "noticias": ex.noticias,
    }


def reconstruir_csv():
    pasta = os.path.join(RAIZ, "dados")
    linhas = []
    for nome in sorted(os.listdir(pasta)):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", nome):
            ed = json.loads(ler(os.path.join(pasta, nome)))
            for n in ed["noticias"]:
                linhas.append([ed["data"], n["tipo"], n["editoria"], n["titulo"], n["linha_fina"],
                               n["texto"], n["fonte"], n["link"], ed["pagina"]])
    with open(os.path.join(pasta, "noticias.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["data_das_noticias", "tipo", "editoria", "titulo", "linha_fina", "resumo",
                    "fonte", "link_da_fonte", "pagina_da_edicao"])
        w.writerows(linhas)
    return len(linhas)


def reconstruir_arquivo(pagina_modelo):
    """Página edicoes/index.html no mesmo visual (reaproveita <head> e <style> da edição)."""
    pasta = os.path.join(RAIZ, "dados")
    eds = [json.loads(ler(os.path.join(pasta, n))) for n in sorted(os.listdir(pasta), reverse=True)
           if re.fullmatch(r"\d{4}-\d{2}-\d{2}\.json", n)]
    cabeca = pagina_modelo.split("</head>", 1)[0]
    cabeca = re.sub(r"<title>.*?</title>", "<title>Edições anteriores — Newsletter diária</title>", cabeca, flags=re.S)
    itens = []
    for ed in eds:
        man = next((n for n in ed["noticias"] if n["tipo"] == "manchete"), None)
        dia = ed["data"][8:10] + "/" + ed["data"][5:7] + "/" + ed["data"][:4]
        itens.append(
            f'<li><a href="{ed["data"]}.html"><span class="kick">{html.escape(dia)} · '
            f'{len(ed["noticias"])} notícias</span><span class="dt">'
            f'{html.escape(ed["data_por_extenso"])}</span>'
            + (f'<span class="ar-man">{html.escape(man["titulo"])}</span>' if man else "")
            + "</a></li>")
    corpo = f"""</head>
<body>
<style>
.arq{{padding-block:28px 60px}}
.arq ol{{list-style:none;margin:0;padding:0;display:grid;gap:10px}}
.arq a{{display:flex;flex-direction:column;gap:6px;padding:16px 18px;border-radius:16px;background:var(--paper);text-decoration:none;--c:var(--accent);
  transition:transform .4s var(--ease),box-shadow .4s var(--ease)}}
.arq a:hover{{transform:translateY(-3px);box-shadow:var(--shadow)}}
.arq .dt{{font-family:var(--f-head);font-weight:700;font-size:1.02rem}}
.ar-man{{font-size:.95rem;color:var(--muted)}}
.arq-links{{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 20px;font-family:var(--f-head);font-size:.85rem}}
.arq-links a{{display:inline-flex;align-items:center;min-height:44px;padding:0 16px;border-radius:999px;background:var(--paper);text-decoration:none;color:var(--ink)}}
</style>
<header class="masthead" id="topo"><div class="wrap">
  <p class="brand">Newsletter diária</p>
  <p class="date">Edições anteriores</p>
</div></header>
<main><div class="wrap arq">
  <p class="arq-links"><a href="../">← Edição de hoje</a><a href="../dados/noticias.csv">Baixar todas as notícias (CSV)</a></p>
  <ol>{''.join(itens)}</ol>
</div></main>
</body>
</html>
"""
    gravar(os.path.join(RAIZ, "edicoes", "index.html"), cabeca + corpo)
    return len(eds)


def com_link_arquivo(pagina):
    """Acrescenta o link 'Edições anteriores' no rodapé da página principal."""
    marca = '<p class="arq-link">'
    if marca in pagina:
        return pagina
    link = (marca + '<a href="edicoes/" style="color:var(--ink);font-weight:600">'
            'Edições anteriores e banco de notícias →</a></p>\n')
    return pagina.replace("</div></footer>", link + "</div></footer>", 1)


def main():
    if len(sys.argv) != 3 or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", sys.argv[2]):
        sys.exit(__doc__)
    origem, data = sys.argv[1], sys.argv[2]
    pagina = ler(origem)
    destino = os.path.join(RAIZ, "edicoes", f"{data}.html")
    if os.path.exists(destino) and ler(destino) != pagina:
        print(f"Aviso: edicoes/{data}.html já existia e foi substituída.")
    gravar(destino, pagina)
    gravar(os.path.join(RAIZ, "index.html"), com_link_arquivo(pagina))
    dados = extrair(pagina, data)
    gravar(os.path.join(RAIZ, "dados", f"{data}.json"), json.dumps(dados, ensure_ascii=False, indent=2) + "\n")
    total = reconstruir_csv()
    n_eds = reconstruir_arquivo(pagina)
    open(os.path.join(RAIZ, ".nojekyll"), "a").close()
    print(f"Edição {data}: {len(dados['noticias'])} notícias, {len(dados['destaques'])} destaques. "
          f"Banco: {n_eds} edição(ões), {total} notícias.")


if __name__ == "__main__":
    main()
