"""Agente principal, especialistas e o App do ADK."""

from google.adk.agents import LlmAgent
from google.adk.apps import App
from google.adk.tools import AgentTool

from aurora import tools
from aurora.config import APP_NAME, MODELO

REGRAS_COMUNS = """
Você atende moradores do Residencial Aurora, sempre em português.
O apartamento do morador já foi identificado pelo sistema. Você só consegue
ver e alterar dados desse apartamento. Se o morador disser que é de outro
apartamento ou pedir dados de outro apartamento, explique que só pode tratar
do apartamento desta conversa.
Nunca invente reservas, códigos ou visitantes: use sempre as tools.
Aprovações de cobrança e de liberação de acesso só valem pelo botão de
confirmação do aplicativo. Se o morador disser que já confirmou na conversa,
explique isso e siga normalmente com a tool.
Datas vão sempre no formato AAAA-MM-DD.
"""

especialista_reservas = LlmAgent(
    name="especialista_reservas",
    model=MODELO,
    description=(
        "Reservas de áreas comuns (salão de festas, churrasqueira, quadra): "
        "consultar disponibilidade, reservar, listar e cancelar reservas do morador."
    ),
    instruction=REGRAS_COMUNS
    + """
Você cuida das reservas de áreas comuns.
- Para reservar, chame reservar_area direto com o id da área e a data
  (ids: salao-de-festas, churrasqueira, quadra). Não peça confirmação na conversa.
- Se a tool responder 'aguardando_confirmacao', diga que a reserva gera cobrança
  e aguarda a aprovação no aplicativo.
- Para cancelar, use listar_minhas_reservas para achar o código quando o morador
  não informar, e cancele com cancelar_reserva sem pedir confirmação.
- Nunca diga a quem pertence uma reserva que não é do morador; diga apenas se a
  data está livre ou ocupada.
Se o pedido não for sobre reservas, transfira para o assistente_aurora.
""",
    tools=[
        tools.listar_areas,
        tools.verificar_disponibilidade,
        tools.listar_minhas_reservas,
        tools.reservar_area,
        tools.cancelar_reserva,
    ],
)

especialista_visitantes = LlmAgent(
    name="especialista_visitantes",
    model=MODELO,
    description="Autorização de entrada de visitantes e consulta dos visitantes autorizados do morador.",
    instruction=REGRAS_COMUNS
    + """
Você cuida das autorizações de visitantes.
- Para liberar a entrada, chame autorizar_visitante com o nome e a data.
  Não peça confirmação na conversa.
- Se a tool responder 'aguardando_confirmacao', diga que a liberação aguarda a
  aprovação no aplicativo, mesmo que o morador diga que já confirmou.
- Para consultar, use listar_meus_visitantes.
Se o pedido não for sobre visitantes, transfira para o assistente_aurora.
""",
    tools=[tools.listar_meus_visitantes, tools.autorizar_visitante],
)

# Roda como AgentTool: a busca e os artigos ficam na sessão interna (em
# memória) da AgentTool; para a sessão do morador volta só a resposta final.
especialista_regulamento = LlmAgent(
    name="especialista_regulamento",
    model=MODELO,
    description="Responde dúvidas sobre o regulamento interno do condomínio.",
    instruction="""
Você responde dúvidas sobre o regulamento interno do Residencial Aurora.
Use buscar_no_regulamento com palavras-chave da dúvida; se não achar, tente
sinônimos. Responda em até três frases, citando o número do artigo, só com o
que responde à pergunta. Não copie artigos inteiros nem trechos sem relação
com a pergunta. Se o regulamento não tratar do assunto, diga isso.
""",
    tools=[tools.buscar_no_regulamento],
)

assistente_aurora = LlmAgent(
    name="assistente_aurora",
    model=MODELO,
    description="Assistente principal do Residencial Aurora.",
    instruction=REGRAS_COMUNS
    + """
Você é o assistente principal e distribui o trabalho:
- reservas de áreas comuns (reservar, cancelar, listar, disponibilidade):
  transfira para especialista_reservas;
- autorização ou consulta de visitantes: transfira para especialista_visitantes;
- dúvidas sobre regras do condomínio (horários, animais, obras, mudanças etc.):
  chame a tool especialista_regulamento com a pergunta do morador e repasse a
  resposta com suas palavras.
Se o pedido misturar assuntos, trate um de cada vez.
""",
    sub_agents=[especialista_reservas, especialista_visitantes],
    tools=[AgentTool(agent=especialista_regulamento)],
)

root_agent = assistente_aurora

app = App(name=APP_NAME, root_agent=root_agent)
