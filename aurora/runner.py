"""Runner com roteamento determinístico entre agente principal e especialistas.

O Runner do ADK 2.2.0 decide quem continua a conversa olhando o último
evento da sessão. Com a sessão em SQLite os eventos voltam ordenados por
timestamp, e o pedido de confirmação (adk_request_confirmation) pode ficar
depois da resposta da tool que o originou. Aí o Runner não reconhece a
retomada e entrega a resposta ao agente principal, que não tem a tool: a
confirmação é consumida e a ação não executa.

Aqui a regra é explícita:
- resposta de confirmação -> o agente que pediu a confirmação;
- mensagem de texto nova   -> sempre o agente principal.
"""

from contextvars import ContextVar

from google.adk.agents import BaseAgent
from google.adk.flows.llm_flows.functions import find_event_by_function_call_id
from google.adk.runners import Runner
from google.adk.sessions import Session

# id do pedido de confirmação que está sendo respondido nesta execução.
confirmacao_em_resposta: ContextVar[str | None] = ContextVar(
    "confirmacao_em_resposta", default=None
)


class AuroraRunner(Runner):
    def _find_agent_to_run(self, session: Session, root_agent: BaseAgent) -> BaseAgent:
        id_confirmacao = confirmacao_em_resposta.get()
        if id_confirmacao:
            evento = find_event_by_function_call_id(session.events, id_confirmacao)
            if evento and (agente := root_agent.find_agent(evento.author)):
                return agente
        return root_agent
