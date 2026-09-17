"""Busca por palavras-chave nos artigos do regulamento.

O regulamento é quebrado em artigos (com o título do capítulo) e só os
artigos mais relevantes para a pergunta são devolvidos.
"""

import re
import unicodedata
from functools import lru_cache

from aurora.config import ARQUIVO_REGULAMENTO

STOPWORDS = {
    "a", "o", "as", "os", "um", "uma", "de", "da", "do", "das", "dos", "e", "em",
    "no", "na", "nos", "nas", "para", "por", "com", "que", "qual", "quais", "se",
    "ate", "como", "quando", "onde", "pode", "posso", "sao", "ser", "ao", "aos",
    "horas", "hora", "horario", "regra", "regras", "regulamento", "funciona",
    "sobre", "meu", "minha", "eu", "ou", "tem", "ha", "mais", "menos", "e",
}


def _normalizar(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return sem_acento.lower()


def _radicais(texto: str) -> set[str]:
    palavras = re.findall(r"[a-z0-9]+", _normalizar(texto))
    # Radical grosseiro: sem o "s" final e cortado em 5 caracteres
    # ("domingos" ~ "domingo", "obras" ~ "obra").
    return {
        p.removesuffix("s")[:5]
        for p in palavras
        if p not in STOPWORDS and len(p) > 2
    }


@lru_cache
def artigos() -> list[dict]:
    capitulo = ""
    lista: list[dict] = []
    for linha in ARQUIVO_REGULAMENTO.read_text(encoding="utf-8").splitlines():
        if linha.startswith("## "):
            capitulo = linha[3:].strip()
            continue
        inicio = re.match(r"\*\*(Art\. \d+\.?)\*\*", linha)
        if inicio:
            lista.append({"capitulo": capitulo, "texto": linha.strip()})
        elif lista and linha.strip() and lista[-1]["capitulo"] == capitulo:
            lista[-1]["texto"] += "\n" + linha.strip()
    for artigo in lista:
        artigo["radicais_texto"] = _radicais(artigo["texto"])
        artigo["radicais_capitulo"] = _radicais(artigo["capitulo"])
    return lista


def buscar(pergunta: str, limite: int = 3) -> list[dict]:
    termos = _radicais(pergunta)
    if not termos:
        return []
    pontuados = []
    for artigo in artigos():
        pontos = len(termos & artigo["radicais_texto"])
        pontos += 2 * len(termos & artigo["radicais_capitulo"])
        if pontos:
            pontuados.append((pontos, artigo))
    if not pontuados:
        return []
    pontuados.sort(key=lambda item: item[0], reverse=True)
    melhor = pontuados[0][0]
    return [
        {"capitulo": a["capitulo"], "texto": a["texto"]}
        for pontos, a in pontuados[:limite]
        if pontos >= melhor * 0.6
    ]
