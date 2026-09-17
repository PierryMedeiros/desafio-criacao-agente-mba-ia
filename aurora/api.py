"""API HTTP do assistente do Residencial Aurora.

Subir: uv run uvicorn aurora.api:app --port 8000
"""

import asyncio
from collections import defaultdict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from google.adk.flows.llm_flows.functions import REQUEST_CONFIRMATION_FUNCTION_CALL_NAME
from google.adk.runners import Runner
from google.adk.sessions.sqlite_session_service import SqliteSessionService
from google.genai import types
from pydantic import BaseModel

from aurora import condominio
from aurora.agentes import app as adk_app
from aurora.config import APP_NAME, ARQUIVO_CONDOMINIO, ARQUIVO_SESSOES, DIR_VAR
from aurora.tools import CHAVE_APARTAMENTO

# O apartamento fica no state da sessão; o user_id do ADK é fixo porque a
# API localiza a sessão só pelo session_id.
USER_ID = "morador"

DIR_VAR.mkdir(parents=True, exist_ok=True)
session_service = SqliteSessionService(str(ARQUIVO_SESSOES))
runner = Runner(app=adk_app, session_service=session_service)

# Uma execução por sessão de cada vez: evita que duas respostas para a mesma
# confirmação sejam processadas em paralelo.
travas: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if not ARQUIVO_CONDOMINIO.exists():
        condominio.restaurar()
    yield
    await runner.close()


app = FastAPI(title="Residencial Aurora", lifespan=lifespan)


class NovaSessao(BaseModel):
    apartamento: str


class NovaMensagem(BaseModel):
    texto: str


class RespostaConfirmacao(BaseModel):
    id: str
    confirmado: bool


async def _sessao(session_id: str):
    sessao = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    if sessao is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    return sessao


def confirmacoes_pendentes(sessao) -> list[dict]:
    """Pedidos de confirmação do ADK que ainda não receberam resposta.

    Tudo sai dos eventos gravados: um pedido é um function call
    adk_request_confirmation; uma resposta é um function response do
    usuário com o mesmo id. Depois de respondido, o id deixa de estar
    pendente, e a rota de confirmações passa a recusá-lo com 409.
    """
    pedidos: dict[str, dict] = {}
    respondidos: set[str] = set()
    for evento in sessao.events:
        for chamada in evento.get_function_calls():
            if chamada.name == REQUEST_CONFIRMATION_FUNCTION_CALL_NAME:
                pedidos[chamada.id] = chamada.args or {}
        if evento.author == "user":
            for resposta in evento.get_function_responses():
                if resposta.name == REQUEST_CONFIRMATION_FUNCTION_CALL_NAME:
                    respondidos.add(resposta.id)

    pendentes = []
    for id_, args in pedidos.items():
        if id_ in respondidos:
            continue
        original = args.get("originalFunctionCall", {})
        confirmacao = args.get("toolConfirmation", {})
        payload = confirmacao.get("payload") or {}
        pendentes.append(
            {
                "id": id_,
                "acao": payload.get("acao", original.get("name", "")),
                "detalhes": payload.get("detalhes", original.get("args", {})),
            }
        )
    return pendentes


async def _executar(session_id: str, mensagem: types.Content) -> dict:
    textos = []
    async for evento in runner.run_async(
        user_id=USER_ID, session_id=session_id, new_message=mensagem
    ):
        if evento.partial or not evento.content or evento.author == "user":
            continue
        for parte in evento.content.parts or []:
            if parte.text and not parte.thought:
                textos.append(parte.text.strip())
    sessao = await _sessao(session_id)
    return {
        "resposta": "\n\n".join(t for t in textos if t),
        "confirmacoes_pendentes": confirmacoes_pendentes(sessao),
    }


@app.post("/sessoes", status_code=201)
async def criar_sessao(corpo: NovaSessao):
    if not condominio.apartamento_existe(corpo.apartamento):
        raise HTTPException(status_code=422, detail="Apartamento inexistente.")
    sessao = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={CHAVE_APARTAMENTO: corpo.apartamento},
    )
    return {"session_id": sessao.id}


@app.post("/sessoes/{session_id}/mensagens")
async def enviar_mensagem(session_id: str, corpo: NovaMensagem):
    async with travas[session_id]:
        await _sessao(session_id)
        mensagem = types.Content(role="user", parts=[types.Part(text=corpo.texto)])
        return await _executar(session_id, mensagem)


@app.post("/sessoes/{session_id}/confirmacoes")
async def responder_confirmacao(session_id: str, corpo: RespostaConfirmacao):
    async with travas[session_id]:
        sessao = await _sessao(session_id)
        pendentes = {p["id"] for p in confirmacoes_pendentes(sessao)}
        if corpo.id not in pendentes:
            raise HTTPException(
                status_code=409,
                detail="Não existe confirmação pendente com esse id nesta sessão.",
            )
        resposta = types.FunctionResponse(
            id=corpo.id,
            name=REQUEST_CONFIRMATION_FUNCTION_CALL_NAME,
            response={"confirmed": corpo.confirmado},
        )
        mensagem = types.Content(role="user", parts=[types.Part(function_response=resposta)])
        return await _executar(session_id, mensagem)


@app.get("/sessoes/{session_id}/eventos")
async def listar_eventos(session_id: str):
    sessao = await _sessao(session_id)
    return [e.model_dump(mode="json", exclude_none=True) for e in sessao.events]


@app.get("/apartamentos/{numero}/reservas")
async def reservas_do_apartamento(numero: str):
    if not condominio.apartamento_existe(numero):
        raise HTTPException(status_code=404, detail="Apartamento inexistente.")
    return condominio.reservas_do_apartamento(numero)


@app.get("/apartamentos/{numero}/visitantes")
async def visitantes_do_apartamento(numero: str):
    if not condominio.apartamento_existe(numero):
        raise HTTPException(status_code=404, detail="Apartamento inexistente.")
    return condominio.visitantes_do_apartamento(numero)
