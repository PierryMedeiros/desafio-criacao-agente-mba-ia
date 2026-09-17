"""Tools dos especialistas.

Regras que não dependem do modelo:
- o apartamento vem sempre de tool_context.state (gravado na criação da
  sessão), nunca de um argumento que o modelo possa preencher;
- ações que geram cobrança ou liberam acesso pedem confirmação pelo
  mecanismo de confirmação do ADK e só executam quando a resposta chega
  pela rota de confirmações.
"""

import re
import unicodedata
from datetime import date

from google.adk.tools import ToolContext

from aurora import condominio, regulamento

CHAVE_APARTAMENTO = "apartamento"


def _apartamento(tool_context: ToolContext) -> str:
    return tool_context.state[CHAVE_APARTAMENTO]


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")


def _resolver_area(area: str) -> dict | None:
    """Aceita o id ('salao-de-festas') ou o nome ('Salão de festas')."""
    chave = _normalizar(area)
    for item in condominio.listar_areas():
        if chave in (item["id"], _normalizar(item["nome"])):
            return item
    for item in condominio.listar_areas():
        if chave and (chave in item["id"] or item["id"] in chave):
            return item
    return None


def _data_valida(data: str) -> bool:
    try:
        return date.fromisoformat(data).isoformat() == data
    except ValueError:
        return False


# ---------------------------------------------------------------- reservas


def listar_areas() -> dict:
    """Lista as áreas comuns reserváveis, com id, nome e taxa em reais.

    Use para descobrir o id de uma área ou se ela tem taxa.
    """
    return {"areas": condominio.listar_areas()}


def verificar_disponibilidade(area: str, data: str) -> dict:
    """Informa se uma área comum está livre em uma data.

    Args:
        area: id da área (ex.: 'salao-de-festas', 'churrasqueira', 'quadra').
        data: data no formato AAAA-MM-DD.
    """
    item = _resolver_area(area)
    if item is None:
        return {"erro": "Área não encontrada. Use listar_areas para ver as opções."}
    if not _data_valida(data):
        return {"erro": "Data inválida. Use o formato AAAA-MM-DD."}
    ocupada = condominio.data_ocupada(item["id"], data)
    return {"area": item["id"], "data": data, "disponivel": not ocupada}


def listar_minhas_reservas(tool_context: ToolContext) -> dict:
    """Lista as reservas ativas do apartamento do morador desta conversa."""
    return {"reservas": condominio.reservas_do_apartamento(_apartamento(tool_context))}


def reservar_area(area: str, data: str, tool_context: ToolContext) -> dict:
    """Reserva uma área comum para o apartamento do morador desta conversa.

    Áreas com taxa só são reservadas depois que o morador aprovar a
    confirmação no aplicativo; nesse caso a tool devolve status
    'aguardando_confirmacao' e nada é gravado até a aprovação.

    Args:
        area: id da área (ex.: 'salao-de-festas', 'churrasqueira', 'quadra').
        data: data no formato AAAA-MM-DD.
    """
    item = _resolver_area(area)
    if item is None:
        return {"erro": "Área não encontrada. Use listar_areas para ver as opções."}
    if not _data_valida(data):
        return {"erro": "Data inválida. Use o formato AAAA-MM-DD."}
    if condominio.data_ocupada(item["id"], data):
        return {"erro": f"A área {item['nome']} já está ocupada em {data}."}

    if item["taxa"] > 0:
        confirmacao = tool_context.tool_confirmation
        if confirmacao is None:
            tool_context.request_confirmation(
                hint=(
                    f"Reservar {item['nome']} em {data} gera cobrança de "
                    f"R$ {item['taxa']:.2f}. Aprovar?"
                ),
                payload={
                    "acao": "reservar_area",
                    "detalhes": {
                        "area": item["id"],
                        "data": data,
                        "taxa": item["taxa"],
                    },
                },
            )
            return {
                "status": "aguardando_confirmacao",
                "mensagem": "A reserva gera cobrança e aguarda a aprovação do morador no aplicativo.",
            }
        if not confirmacao.confirmed:
            return {"status": "negada", "mensagem": "O morador não aprovou a reserva. Nada foi gravado."}

    reserva = condominio.criar_reserva(_apartamento(tool_context), item["id"], data)
    if reserva is None:
        return {"erro": f"A área {item['nome']} já está ocupada em {data}."}
    return {
        "status": "reservada",
        "reserva": reserva,
        "cobranca": item["taxa"] if item["taxa"] > 0 else None,
    }


def cancelar_reserva(codigo: str, tool_context: ToolContext) -> dict:
    """Cancela uma reserva do apartamento do morador desta conversa.

    Só reservas do próprio apartamento podem ser canceladas. Use
    listar_minhas_reservas para descobrir o código.

    Args:
        codigo: código da reserva (ex.: 'RSV-1377').
    """
    cancelada = condominio.cancelar_reserva(
        _apartamento(tool_context), codigo.strip().upper()
    )
    if cancelada is None:
        # A mesma mensagem para "não existe" e "é de outro apartamento".
        return {"erro": "Não há reserva ativa com esse código entre as reservas deste apartamento."}
    return {"status": "cancelada", "reserva": cancelada}


# -------------------------------------------------------------- visitantes


def listar_meus_visitantes(tool_context: ToolContext) -> dict:
    """Lista os visitantes autorizados do apartamento do morador desta conversa."""
    return {"visitantes": condominio.visitantes_do_apartamento(_apartamento(tool_context))}


def autorizar_visitante(nome: str, data: str, tool_context: ToolContext) -> dict:
    """Autoriza a entrada de um visitante no prédio em uma data.

    Toda autorização só é gravada depois que o morador aprovar a
    confirmação no aplicativo; até lá a tool devolve status
    'aguardando_confirmacao'. O que o morador escreve na conversa não
    substitui essa aprovação.

    Args:
        nome: nome completo do visitante.
        data: data da visita no formato AAAA-MM-DD.
    """
    nome = nome.strip()
    if not nome:
        return {"erro": "Informe o nome do visitante."}
    if not _data_valida(data):
        return {"erro": "Data inválida. Use o formato AAAA-MM-DD."}

    confirmacao = tool_context.tool_confirmation
    if confirmacao is None:
        tool_context.request_confirmation(
            hint=f"Liberar a entrada de {nome} em {data}. Aprovar?",
            payload={
                "acao": "autorizar_visitante",
                "detalhes": {"nome": nome, "data": data},
            },
        )
        return {
            "status": "aguardando_confirmacao",
            "mensagem": "A liberação aguarda a aprovação do morador no aplicativo.",
        }
    if not confirmacao.confirmed:
        return {"status": "negada", "mensagem": "O morador não aprovou a liberação. Nada foi gravado."}

    visitante = condominio.autorizar_visitante(_apartamento(tool_context), nome, data)
    return {"status": "autorizado", "visitante": visitante}


# ------------------------------------------------------------- regulamento


def buscar_no_regulamento(termos: str) -> dict:
    """Busca artigos do regulamento interno por palavras-chave.

    Devolve no máximo três artigos. Se nada vier, tente sinônimos.

    Args:
        termos: palavras-chave da dúvida (ex.: 'piscina domingo horário').
    """
    encontrados = regulamento.buscar(termos)
    if not encontrados:
        return {"artigos": [], "aviso": "Nenhum artigo encontrado para esses termos."}
    return {"artigos": encontrados}
