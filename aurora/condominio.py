"""Acesso aos dados do condomínio (SQLite).

Todas as funções que leem ou gravam dados de um apartamento recebem o
apartamento explicitamente; quem chama (as tools) pega esse valor do state
da sessão, nunca do modelo.
"""

import json
import secrets
import sqlite3
from contextlib import contextmanager

from aurora.config import ARQUIVO_CONDOMINIO, DIR_DADOS_INICIAIS, DIR_VAR

LETRAS = "ABCDEFGHJKLMNPQRSTUVWXYZ"

SCHEMA = """
CREATE TABLE apartamentos (numero TEXT PRIMARY KEY, morador TEXT NOT NULL);
CREATE TABLE areas (id TEXT PRIMARY KEY, nome TEXT NOT NULL, taxa REAL NOT NULL);
-- Reservas canceladas ficam com cancelada = 1 para que o código nunca seja reaproveitado.
CREATE TABLE reservas (
    codigo TEXT PRIMARY KEY,
    apartamento TEXT NOT NULL REFERENCES apartamentos(numero),
    area TEXT NOT NULL REFERENCES areas(id),
    data TEXT NOT NULL,
    cancelada INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX reserva_ativa_por_data ON reservas(area, data) WHERE cancelada = 0;
CREATE TABLE visitantes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartamento TEXT NOT NULL REFERENCES apartamentos(numero),
    nome TEXT NOT NULL,
    data TEXT NOT NULL
);
"""


@contextmanager
def conectar():
    conn = sqlite3.connect(ARQUIVO_CONDOMINIO)
    conn.row_factory = sqlite3.Row
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def restaurar() -> None:
    """Recria o banco do condomínio a partir dos arquivos de dados/."""
    DIR_VAR.mkdir(parents=True, exist_ok=True)
    ARQUIVO_CONDOMINIO.unlink(missing_ok=True)

    def ler(nome):
        return json.loads((DIR_DADOS_INICIAIS / nome).read_text(encoding="utf-8"))

    with conectar() as conn:
        conn.executescript(SCHEMA)
        conn.executemany(
            "INSERT INTO apartamentos VALUES (:numero, :morador)",
            ler("apartamentos.json"),
        )
        conn.executemany(
            "INSERT INTO areas VALUES (:id, :nome, :taxa)", ler("areas.json")
        )
        conn.executemany(
            "INSERT INTO reservas (codigo, apartamento, area, data)"
            " VALUES (:codigo, :apartamento, :area, :data)",
            ler("reservas.json"),
        )
        conn.executemany(
            "INSERT INTO visitantes (apartamento, nome, data)"
            " VALUES (:apartamento, :nome, :data)",
            ler("visitantes.json"),
        )


def apartamento_existe(numero: str) -> bool:
    with conectar() as conn:
        return (
            conn.execute(
                "SELECT 1 FROM apartamentos WHERE numero = ?", (numero,)
            ).fetchone()
            is not None
        )


def listar_areas() -> list[dict]:
    with conectar() as conn:
        rows = conn.execute("SELECT id, nome, taxa FROM areas ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def buscar_area(area_id: str) -> dict | None:
    with conectar() as conn:
        row = conn.execute(
            "SELECT id, nome, taxa FROM areas WHERE id = ?", (area_id,)
        ).fetchone()
    return dict(row) if row else None


def data_ocupada(area_id: str, data: str) -> bool:
    """Diz só se a data está ocupada, sem revelar de quem é a reserva."""
    with conectar() as conn:
        row = conn.execute(
            "SELECT 1 FROM reservas WHERE area = ? AND data = ? AND cancelada = 0",
            (area_id, data),
        ).fetchone()
    return row is not None


def reservas_do_apartamento(apartamento: str) -> list[dict]:
    with conectar() as conn:
        rows = conn.execute(
            "SELECT codigo, area, data FROM reservas"
            " WHERE apartamento = ? AND cancelada = 0 ORDER BY data, codigo",
            (apartamento,),
        ).fetchall()
    return [dict(r) for r in rows]


def _novo_codigo(conn) -> str:
    while True:
        # Só letras: um código nunca se confunde com número de apartamento.
        codigo = "RSV-" + "".join(secrets.choice(LETRAS) for _ in range(6))
        existe = conn.execute(
            "SELECT 1 FROM reservas WHERE codigo = ?", (codigo,)
        ).fetchone()
        if not existe:
            return codigo


def criar_reserva(apartamento: str, area_id: str, data: str) -> dict | None:
    """Grava a reserva. Devolve None se a data já estiver ocupada."""
    with conectar() as conn:
        codigo = _novo_codigo(conn)
        try:
            conn.execute(
                "INSERT INTO reservas (codigo, apartamento, area, data)"
                " VALUES (?, ?, ?, ?)",
                (codigo, apartamento, area_id, data),
            )
        except sqlite3.IntegrityError:
            return None
    return {"codigo": codigo, "area": area_id, "data": data}


def cancelar_reserva(apartamento: str, codigo: str) -> dict | None:
    """Cancela só se a reserva ativa for do apartamento informado."""
    with conectar() as conn:
        row = conn.execute(
            "SELECT codigo, area, data FROM reservas"
            " WHERE codigo = ? AND apartamento = ? AND cancelada = 0",
            (codigo, apartamento),
        ).fetchone()
        if row is None:
            return None
        conn.execute("UPDATE reservas SET cancelada = 1 WHERE codigo = ?", (codigo,))
    return dict(row)


def visitantes_do_apartamento(apartamento: str) -> list[dict]:
    with conectar() as conn:
        rows = conn.execute(
            "SELECT nome, data FROM visitantes WHERE apartamento = ? ORDER BY data, id",
            (apartamento,),
        ).fetchall()
    return [dict(r) for r in rows]


def autorizar_visitante(apartamento: str, nome: str, data: str) -> dict:
    with conectar() as conn:
        conn.execute(
            "INSERT INTO visitantes (apartamento, nome, data) VALUES (?, ?, ?)",
            (apartamento, nome, data),
        )
    return {"nome": nome, "data": data}
