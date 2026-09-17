"""Restaura o estado inicial: dados do condomínio e sessões zeradas.

Uso: uv run python -m aurora.restaurar
"""

from aurora import condominio
from aurora.config import ARQUIVO_SESSOES


def main() -> None:
    condominio.restaurar()
    ARQUIVO_SESSOES.unlink(missing_ok=True)
    print("Dados iniciais restaurados e sessões apagadas.")


if __name__ == "__main__":
    main()
