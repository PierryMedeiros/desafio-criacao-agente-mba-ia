"""Caminhos e configuração compartilhados pela aplicação."""

import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent

# Um Runner próprio não lê o .env sozinho, como o adk web faz.
load_dotenv(RAIZ / ".env")

DIR_DADOS_INICIAIS = RAIZ / "dados"
DIR_VAR = Path(os.getenv("AURORA_DIR_VAR", RAIZ / "var"))
ARQUIVO_CONDOMINIO = DIR_VAR / "condominio.db"
ARQUIVO_SESSOES = DIR_VAR / "sessoes.db"
ARQUIVO_REGULAMENTO = DIR_DADOS_INICIAIS / "regulamento.md"

APP_NAME = "residencial_aurora"
MODELO = os.getenv("AURORA_MODELO") or "gemini-3.1-flash-lite"
