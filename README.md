# Residencial Aurora: assistente virtual com Google ADK

API em Python (FastAPI) com um assistente construído com Google ADK 2.2.0.
Pelo chat, o morador reserva e cancela áreas comuns, autoriza visitantes e tira
dúvidas sobre o regulamento. As regras críticas ficam no código: o modelo
escolhe o caminho, e o código decide o que é permitido.

```
aurora/
  api.py          rotas HTTP, confirmações pendentes, Runner
  runner.py       Runner com roteamento determinístico (confirmação -> especialista)
  agentes.py      agente principal, especialistas e App do ADK
  tools.py        tools dos especialistas (única forma de ler/gravar dados)
  condominio.py   banco SQLite do condomínio
  regulamento.py  busca de artigos do regulamento por palavras-chave
  restaurar.py    comando de restauração dos dados iniciais
  config.py       caminhos, modelo e carga do .env
dados/            estado inicial do condomínio (não é alterado)
var/              bancos SQLite gerados em tempo de execução (fora do Git)
```

## Arquitetura

```
morador ──HTTP──> FastAPI (aurora/api.py)
                      │  AuroraRunner + SqliteSessionService (var/sessoes.db)
                      ▼
             assistente_aurora (agente principal, modo chat)
              ├─ transfer_to_agent ─> especialista_reservas   ─┐
              ├─ transfer_to_agent ─> especialista_visitantes ─┼─ tools ─> var/condominio.db
              └─ AgentTool ─────────> especialista_regulamento ─── tool ──> dados/regulamento.md
```

| Agente | Responsabilidade | Como é acionado | Por quê |
|---|---|---|---|
| `assistente_aurora` | Conversa com o morador e distribui o trabalho. Não tem tools de dados nem o regulamento nas instruções. | Toda mensagem de texto nova começa nele (`aurora/runner.py`). | Um ponto de entrada único deixa o roteamento previsível. |
| `especialista_reservas` | Lista áreas, verifica disponibilidade, lista, cria e cancela reservas do apartamento da sessão. | `transfer_to_agent` (sub-agente em modo chat). | Precisa conversar com o morador e pedir confirmação de tool. Com a transferência, o pedido de confirmação e a retomada acontecem no próprio especialista, dentro da sessão do morador. |
| `especialista_visitantes` | Lista e autoriza visitantes do apartamento da sessão. | `transfer_to_agent` (sub-agente em modo chat). | Mesmo motivo: autorizar visitante sempre pede confirmação. |
| `especialista_regulamento` | Busca artigos no regulamento e responde em poucas frases. | `AgentTool` chamada pelo agente principal. | A AgentTool roda numa sessão própria em memória. A busca e os artigos lidos ficam nessa sessão, e só a resposta curta volta para a sessão do morador (Garantia 4). |

Os especialistas de reservas e de visitantes têm `disallow_transfer_to_parent`
e `disallow_transfer_to_peers`. Eles respondem e encerram o turno, e a mensagem
seguinte volta ao agente principal. Assim, o morador não fica preso num
especialista quando muda de assunto.

Todos os agentes usam `gemini-3.1-flash-lite` por padrão (configurável em
`AURORA_MODELO`). O modelo roteou bem e faz poucas chamadas por mensagem
(duas ou três), o que cabe no plano gratuito. No desenvolvimento,
`gemini-2.5-flash-lite` travou mais vezes: devolveu resposta vazia depois de
erro de tool e não devolveu o controle ao agente principal.

## Garantias

### Garantia 1: cobrança ou acesso só com confirmação

- `aurora/tools.py`, funções `reservar_area` e `autorizar_visitante`. Quando
  `tool_context.tool_confirmation` é `None`, a tool chama
  `tool_context.request_confirmation(...)` e retorna sem gravar. Só grava
  quando `tool_confirmation.confirmed` é verdadeiro. Em `reservar_area`, a
  confirmação só é pedida quando `item["taxa"] > 0`, e a quadra (taxa 0) grava
  direto. `cancelar_reserva` não pede confirmação.
- `aurora/api.py`, função `confirmacoes_pendentes`. As pendências vêm dos
  eventos gravados: cada function call `adk_request_confirmation` sem
  function response do usuário com o mesmo id. Os `detalhes` vêm do `payload`
  montado pela tool (área e data, ou nome e data).
- `aurora/api.py`, rota `responder_confirmacao`. Se o `id` não está nessa lista
  (inexistente, de outra sessão ou já respondido), a rota devolve `409` antes
  de chamar o Runner. Caso contrário, envia ao Runner um
  `FunctionResponse(name="adk_request_confirmation", response={"confirmed": ...})`.
  Um `asyncio.Lock` por sessão impede que duas respostas simultâneas passem
  pela checagem.
- `aurora/runner.py`, classe `AuroraRunner`. A resposta de confirmação é
  entregue ao agente que pediu a confirmação. Com a sessão em SQLite, os
  eventos voltam ordenados por timestamp, e o Runner padrão do ADK 2.2.0
  entregava a resposta ao agente principal, que não tem a tool: a confirmação
  era consumida e a ação não executava.

Por que não depende do modelo: o modelo só consegue produzir texto e chamadas
de tool. `tool_confirmation` é preenchido pelo ADK apenas a partir de um
function response do usuário, e a API só cria esse function response na rota
de confirmações. Escrever "já confirmei" na conversa não muda nada. Na
aprovação, o ADK reexecuta a chamada original, com os argumentos gravados no
pedido de confirmação, e não uma chamada nova do modelo.

### Garantia 2: cada sessão pertence a um apartamento

- `aurora/api.py`, rota `criar_sessao`. O apartamento é gravado uma vez em
  `state={"apartamento": ...}` na criação da sessão. Nenhuma rota ou tool
  altera essa chave depois.
- `aurora/tools.py`, função `_apartamento(tool_context)`. Todas as tools leem o
  apartamento do state. Nenhuma tool recebe o apartamento como argumento,
  então o modelo não tem como pedir dados de outro apartamento.
- `aurora/condominio.py`, funções `cancelar_reserva` (`WHERE codigo = ? AND
  apartamento = ?`), `reservas_do_apartamento` e `visitantes_do_apartamento`.
- `aurora/tools.py`, funções `verificar_disponibilidade` e `reservar_area`, com
  `condominio.data_ocupada`. Elas devolvem só livre ou ocupada, sem código nem
  apartamento do dono. `cancelar_reserva` responde com a mesma mensagem para
  "não existe" e "é de outro apartamento".

Por que não depende do modelo: o dado de outro apartamento nunca chega ao
modelo, porque nenhuma tool o devolve. Uma ação sobre outro apartamento
também não tem como ser expressa, porque o filtro por apartamento está no SQL
e o valor vem do state.

### Garantia 3: nada se perde no reinício

- `aurora/api.py`: `SqliteSessionService(str(ARQUIVO_SESSOES))` guarda sessões
  e eventos em `var/sessoes.db`, e `AuroraRunner(app=adk_app, ...)` usa o mesmo
  `app_name` da criação da sessão (`APP_NAME` em `aurora/config.py`).
- `aurora/condominio.py`: reservas e visitantes ficam em `var/condominio.db`.
  Reservas canceladas são marcadas com `cancelada = 1` em vez de apagadas, e
  `_novo_codigo` confere o código contra todas as reservas, inclusive as
  canceladas, para que ele nunca se repita. O índice
  `reserva_ativa_por_data` garante uma reserva ativa por área e data.
- `aurora/api.py`, função `lifespan`. Ela só cria o banco do condomínio se ele
  não existir, então subir a API de novo não restaura nada.
- `aurora/agentes.py`: `ResumabilityConfig(is_resumable=True)` permite
  retomar uma confirmação pendente depois do reinício, porque tudo que a
  retomada precisa está nos eventos gravados.

Por que não depende do modelo: o estado fica em arquivos SQLite e não na
memória do processo nem no que o modelo lembra.

### Garantia 4: o regulamento é consultado, não carregado

- `aurora/agentes.py`: `assistente_aurora` não tem o regulamento nas
  instruções. Ele recebe `AgentTool(agent=especialista_regulamento)`.
- `aurora/tools.py`, função `buscar_no_regulamento`, e
  `aurora/regulamento.py`, função `buscar`. O regulamento é quebrado em
  artigos, e só até três artigos relevantes voltam para o especialista.
- A `AgentTool` do ADK executa o especialista num Runner com
  `InMemorySessionService` próprio (`google/adk/tools/agent_tool.py`). A
  chamada de `buscar_no_regulamento` e os artigos retornados ficam nessa
  sessão descartável. Na sessão do morador entram só a chamada
  `especialista_regulamento(request=...)` e a resposta curta dele.

Por que não depende do modelo: o texto do regulamento não está em nenhuma
instrução da sessão do morador, e o código só devolve para essa sessão o
resultado final da AgentTool.

## Como rodar

Pré-requisitos:

- Python 3.12 ou superior
- [uv](https://docs.astral.sh/uv/)
- uma chave do Google AI Studio

Variáveis do `.env`, copiado de `.env.example`:

| Variável | Uso |
|---|---|
| `GOOGLE_API_KEY` | chave do Google AI Studio (obrigatória) |
| `GOOGLE_GENAI_USE_VERTEXAI` | `FALSE`, para usar o AI Studio |
| `AURORA_MODELO` | opcional; modelo de todos os agentes (padrão `gemini-3.1-flash-lite`) |

```bash
cp .env.example .env              # preencha GOOGLE_API_KEY
uv sync

# restaura os dados iniciais (condomínio a partir de dados/ e sessões zeradas)
uv run python -m aurora.restaurar

# sobe a API em http://localhost:8000
uv run uvicorn aurora.api:app --port 8000
```

O armazenamento é SQLite em arquivo (`var/`), então nenhum serviço externo
precisa subir. Se a API subir sem restauração prévia, ela cria o banco do
condomínio a partir de `dados/`. Para reiniciar mantendo os dados, pare a API
(Ctrl+C) e rode de novo só o comando de subida.

Exemplo:

```bash
curl -s -X POST localhost:8000/sessoes -H 'content-type: application/json' -d '{"apartamento":"101"}'
curl -s -X POST localhost:8000/sessoes/<session_id>/mensagens -H 'content-type: application/json' \
  -d '{"texto":"Reserve o salão de festas para 2030-04-20"}'
curl -s -X POST localhost:8000/sessoes/<session_id>/confirmacoes -H 'content-type: application/json' \
  -d '{"id":"<id da confirmação>","confirmado":true}'
```

Decisões do contrato que o enunciado deixou livres:

- `POST /sessoes` com apartamento inexistente responde `422`.
- As rotas de verificação respondem `404` para apartamento inexistente.
- Quando o modelo encerra sem texto, `resposta` usa a mensagem da última tool
  executada.
