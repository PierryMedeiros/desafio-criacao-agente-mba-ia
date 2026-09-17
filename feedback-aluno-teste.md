# Feedback do aluno-teste: "Regra é regra"

- Enunciado testado: `README.md` da `main` no commit `ba153e255335b399dec1bd7b11e3639f951b3d98`.
- Solução: branch `aluno-teste`, com ADK 2.2.0, FastAPI, SQLite e `gemini-3.1-flash-lite`.
- Data: 2026-09-17.

## Tempo

Os horários vêm do comando `date`. Quem fez o teste foi um agente de IA, então
os tempos são muito menores do que os de um aluno humano. Para estimar o
esforço de um aluno, vale mais olhar a proporção entre as etapas e as travas
descritas abaixo.

| Etapa | Início | Fim | Duração |
|---|---|---|---|
| Leitura do enunciado (e dos arquivos de `dados/`) | 13:01:48 | 13:01:58 | ~10 s (a leitura foi feita numa única passada antes de anotar o fim) |
| Trava de ambiente: instalar o uv | 13:02 | 13:05:08 | ~3 min |
| Desenho da arquitetura (inclui leitura do código-fonte do ADK sobre confirmação) | 13:05:08 | 13:07:29 | ~2 min 20 s |
| Implementação (primeira versão completa) | 13:07:29 | 13:10:35 | ~3 min |
| Testes + correções (a implementação continuou em paralelo até 13:19:33) | 13:10:35 | 13:20:30 | ~10 min |
| Fluxo do avaliador (clone limpo, passos 1 a 14) | 13:20:30 | 13:22:10 | ~1 min 40 s |
| **Total** (da leitura ao fim do fluxo do avaliador) | 13:01:48 | 13:22:10 | **~20 min 20 s** |

A escrita deste feedback começou às 13:23. Cerca de metade do tempo de
"testes + correções" foi gasta com a trava 2, a retomada da confirmação com
SQLite. Para um aluno humano, estimo que essa trava custaria de 2 a 6 horas.

## Resultado do fluxo do avaliador

Clone limpo da `aluno-teste` em uma pasta temporária fora do repositório. O
`.env` foi copiado com `cp`. Segui só o README: `uv sync`, depois
`uv run python -m aurora.restaurar` e
`uv run uvicorn aurora.api:app --port 8000`. As chamadas HTTP foram feitas
por um script Python (urllib) que imprime a requisição, a resposta e a
checagem. No passo 12, as frases de capítulos sem relação com a piscina que
escolhi foram:

- "Considera-se período de silêncio" (Cap. III)
- "É permitida a permanência de animais" (Cap. VIII)
- "As mudanças somente podem ser realizadas" (Cap. IX)
- "As obras que produzam ruído" (Cap. X)
- "O lixo doméstico deve ser acondicionado" (Cap. XII)
- "A academia" (Cap. V)
- "Capítulo VII: Portaria"
- "Art. 70"

Também procurei termos do próprio capítulo da piscina que não respondem à
pergunta: "Art. 21", "Art. 23", "Art. 27", "exame dermatológico",
"convidados", "Capítulo", "brinquedoteca" e "garagem".

### Passos

| Passo | Resultado | Evidência |
|---|---|---|
| 1 | Passou | `uv sync` instalou `google-adk==2.2.0`. Restauração: "Dados iniciais restaurados e sessões apagadas." `GET /apartamentos/101/reservas` → 200 `[{"codigo":"RSV-1377","area":"quadra","data":"2030-03-09"}]`. `GET /apartamentos/302/visitantes` → 200 `[{"nome":"Marina Duarte","data":"2030-03-16"}]` |
| 2 | Passou | `POST /sessoes {"apartamento":"101"}` → 201 `{"session_id":"663c689c-…"}` |
| 3 | Passou | A resposta foi "…só tenho acesso aos dados referentes ao apartamento 101…". `vazamentos=[]` na resposta e em `GET /sessoes/{S1}/eventos` |
| 4 | Passou | A resposta foi "…a reserva **RSV-4821** não consta na lista de reservas do apartamento 101…". `GET /apartamentos/302/reservas` → `[{"codigo":"RSV-4821",…}]` |
| 5 | Passou | Uma mensagem, `confirmacoes_pendentes: []`. `GET 101/reservas` → `[]`, sem a RSV-1377 |
| 6 | Passou | "A quadra foi reservada com sucesso para o dia 2030-04-06… RSV-YKKVNF". `confirmacoes_pendentes: []` |
| 7 | Passou | `resposta: ""` com `confirmacoes_pendentes: [{"id":"adk-d28dff24-…","acao":"reservar_area","detalhes":{"area":"salao-de-festas","data":"2030-04-20","taxa":150.0}}]`. Havia 0 reservas do salão em 2030-04-20. Resposta com `false` → 200, e o salão continuou com 0 reservas nessa data |
| 8 | Passou | Nova pendência `adk-a7e2b0e4-…`. Com `true` → 200 "…realizada com sucesso… RSV-QJEWVK", e o salão ficou com 1 reserva em 2030-04-20. Reenvio do mesmo id → 409 `{"detail":"Não existe confirmação pendente com esse id nesta sessão."}`, e o salão continuou com 1 |
| 9 | Passou | `id-inexistente` → 409, reservas iguais. `GET /sessoes/sessao-inexistente/eventos` → 404 |
| 10 | Passou | S2: "O salão de festas já está reservado para o dia 2030-03-16…", sem pendência. O 101 ficou sem salão em 2030-03-16. As respostas não contêm `RSV-4821` nem `302`, e os eventos de S2 não contêm `RSV-4821` |
| 11 | Passou | `resposta: ""` com pendência `{"acao":"autorizar_visitante","detalhes":{"nome":"Joana Ribeiro","data":"2030-04-21"}}`. `GET 101/visitantes` → `[]`. Com `true` → "A entrada da Joana Ribeiro… foi autorizada", e `GET 101/visitantes` → `[{"nome":"Joana Ribeiro","data":"2030-04-21"}]` |
| 12 | Passou | "A piscina do residencial funciona aos domingos das 9h às 20h… (Artigo 22, inciso II)". S1 tinha 65 eventos, com as tools `transfer_to_agent`, `listar_minhas_reservas`, `cancelar_reserva`, `reservar_area`, `adk_request_confirmation`, `autorizar_visitante` e `especialista_regulamento`. Nenhuma das frases escolhidas apareceu. O único conteúdo do regulamento nos eventos é a resposta curta da AgentTool |
| 13 | Passou | API parada com SIGINT e subida de novo com o mesmo comando, sem restaurar. `GET eventos` → 200 com 65 eventos, igual ao anotado. "Quais são as minhas reservas agora?" → 200, e os eventos foram de 65 para 73. 101: quadra 2030-04-06 (RSV-YKKVNF), salão 2030-04-20 (RSV-QJEWVK), sem RSV-1377, Joana Ribeiro em 2030-04-21. 302: RSV-4821. Códigos ativos: `RSV-YKKVNF, RSV-QJEWVK, RSV-2950, RSV-4821`, sem repetição |
| 14 | Passou | `pyproject.toml`: `"google-adk==2.2.0"`, e `uv.lock`: `version = "2.2.0"`. `git diff --quiet ba153e2 HEAD -- dados/` → idênticos. `.env` fora do repositório (`git ls-files` não lista). `.env.example` só com nomes. Nenhum padrão `AIza…`/`AQ.…` nem `GOOGLE_API_KEY=<valor>` em `git log -p --all`. Agente principal com `sub_agents=[especialista_reservas, especialista_visitantes]` e `tools=[AgentTool(especialista_regulamento)]`. As tools leem e gravam reservas e visitantes. Instrução do principal: 1531 caracteres, sem "Art." nem "9h às 20h". A seção Garantias do README cita 28 trechos, todos encontrados por `grep -F` nos arquivos citados |

### Critérios de aceite

| Critério | Resultado | Evidência |
|---|---|---|
| `uv sync` sem erro, ADK exato, série 2, ≥ 2.2.0 | Passou | Passos 1 e 14 |
| Restauração e subida deixam a API em :8000 com os dados iniciais | Passou | Passo 1 |
| `dados/` idênticos ao repositório base | Passou | `git diff --quiet` contra `ba153e2` |
| Nenhuma chave versionada, `.env` fora, `.env.example` com variáveis | Passou | Passo 14 |
| Agente principal + ≥ 2 especialistas | Passou | 2 sub-agentes + 1 AgentTool |
| Reservas e visitantes por tools, e mudanças visíveis nas rotas | Passou | Passos 5, 6, 8, 11 e 14 |
| G1: taxa → pendência com área e data, nada gravado antes | Passou | Passo 7 |
| G1: negar não grava | Passou | Passo 7 |
| G1: aprovar grava exatamente uma | Passou | Passo 8 |
| G1: reenvio → 409 sem reexecutar | Passou | Passo 8 |
| G1: id não pendente → 409 sem alterar | Passou | Passo 9 |
| G1: área sem taxa sem pendência | Passou | Passo 6 |
| G1: visitante → pendência com nome e data, mesmo com "já confirmei" | Passou | Passo 11 |
| G2: dados do 302 não vazam em S1 | Passou | Passo 3 |
| G2: cancelar RSV-4821 não altera o 302 | Passou | Passo 4 |
| G2: cancelar a própria reserva sem pendência | Passou | Passo 5 |
| G2: data ocupada pelo 302 → não reserva, sem RSV-4821/302 | Passou | Passo 10 |
| G3: mesmos eventos depois do reinício e aceita novas mensagens | Passou | Passo 13 |
| G3: dados persistidos, sem código repetido | Passou | Passo 13 |
| G4: horário de fechamento aos domingos | Passou | Passo 12 (20h) |
| G4: eventos com tools e sem trechos sem relação | Passou | Passo 12 |
| G4: principal sem regulamento nas instruções | Passou | Passo 14 |
| Contrato: caminhos, campos, formatos e status | Passou | Passos 2 a 13 (201, 200, 404, 409) |
| README com Arquitetura, Garantias e Como rodar, com trechos existentes | Passou | Passo 14 |

Observação: o passo 7 passou, mas o texto da resposta depois da negação saiu
enganoso ("não foi possível efetivar a cobrança da taxa. Por favor, verifique
se há alguma pendência de aprovação no aplicativo"), embora a tool devolva
"Você não aprovou a cobrança, então a reserva não foi feita". O tom está fora
de escopo, mas um aluno pode estranhar.

## Contradições

Não encontrei requisitos impossíveis de cumprir ao mesmo tempo. Encontrei
trechos que se chocam entre si ou com o próprio fluxo:

1. **Passo 3 × passo 4, nos eventos de S1.** O passo 3 exige que
   "`GET /sessoes/{S1}/eventos` [não contenha] `RSV-4821`", e o passo 4
   manda escrever em S1 "Cancele a reserva RSV-4821 do salão de festas.". Ou
   seja, a partir do passo 4 a checagem do passo 3 falha para qualquer
   solução, porque a mensagem do usuário é um evento. O critério "(passo 3)"
   precisa ser conferido imediatamente. Um avaliador que confira todos os
   critérios no fim reprova todo mundo. Vale dizer isso explicitamente.
2. **Garantia 2 × passo 4.** "nada que o morador escreva faz o assistente […]
   trazer dados deles para a conversa". No passo 4, o próprio morador traz o
   código RSV-4821, e qualquer modelo tende a repeti-lo na resposta ("a
   reserva RSV-4821 não consta…"). Pela letra, isso "traz" um dado do 302
   para a conversa. O fluxo não confere a resposta do passo 4, então na
   prática não reprova, mas o texto e o fluxo não batem.
3. **"Consulte na documentação oficial do Google […] os limites atuais do
   plano gratuito"** × a documentação. A página
   `ai.google.dev/gemini-api/docs/rate-limits` não traz mais os números e
   manda ver no painel do AI Studio (que exige login). A instrução não pode ser
   cumprida como está escrita.
4. **Dica final** "na versão 2.2.0, conferimos confirmação e retomada
   funcionando com sessão persistida em SQLite" × comportamento real. Isso só
   vale para algumas topologias de agentes. Com especialistas que não
   transferem de volta (`disallow_transfer_to_parent=True`, uma escolha
   natural depois da aula de "bloqueio de transferência"), a retomada com
   `SqliteSessionService` **falha em silêncio**: a rota devolve 200, a
   confirmação sai da lista de pendentes e a ação não executa (detalhes na
   trava 2). A frase dá uma segurança que não se sustenta para toda
   arquitetura permitida pelo requisito 1 ("como cada um é acionado são
   decisões suas").
5. **"Repositório base: https://github.com/devfullcycle/REPO-A-DEFINIR"** × o
   entregável "Link do fork público do repositório base". O link é um
   placeholder.

## Pontos vagos

| Ponto | Interpretações possíveis | Adotada |
|---|---|---|
| O que "restaurar os dados iniciais" restaura | (a) só reservas e visitantes; (b) também as sessões | (b): recria o banco do condomínio e apaga as sessões. É o estado inicial completo |
| `POST /sessoes` com apartamento inexistente | 201 mesmo assim; 404; 422 | 422 |
| Rotas de verificação com apartamento inexistente | `[]`; 404 | 404 |
| Ordem das checagens em `/confirmacoes` com sessão inexistente e id inválido | 404 ou 409 | 404 primeiro, porque o contrato diz que rotas com `{session_id}` respondem 404 |
| Formato de "eventos com o conteúdo completo" | Event do ADK serializado; formato próprio | `Event.model_dump(mode="json", exclude_none=True)` do ADK |
| "trechos de artigos sem relação com a pergunta": granularidade | Capítulo (outro assunto) ou artigo (ex.: Art. 23, exame dermatológico, é da piscina mas não responde "até que horas") | A mais estrita, por artigo: nenhum artigo entra na sessão, só a resposta final |
| O que conta como "especialista" | Só sub-agentes com `transfer_to_agent`; qualquer agente, inclusive via AgentTool | Por segurança, 2 sub-agentes + 1 AgentTool |
| `resposta` depois de negar uma confirmação | Vazia; texto do modelo | Texto do modelo, com fallback para a mensagem da tool quando o modelo não gera texto |
| `user_id` do ADK | Apartamento; fixo; session_id | Fixo (`"morador"`), com o apartamento no state. A API só recebe `session_id` |
| Como o avaliador "para a API" no passo 13 | Ctrl+C; kill -9 | Ctrl+C/SIGINT. Com SQLite, as duas formas deveriam funcionar |
| "Checar se uma data está livre": antes ou depois de pedir confirmação | Os dois são aceitos pelo passo 10 ("Se aparecer confirmação pendente, aprova") | Antes e de novo na execução |
| Conteúdo de `detalhes` | Só área e data; incluir taxa | Área, data e taxa |
| Entregável: a lista mistura "Link do fork", "README.md" e as três seções como itens irmãos | Seções do README ou entregáveis separados | Seções do README |
| Checagem de `302` por substring no passo 10 | Qualquer ocorrência de "302" nas respostas, inclusive dentro de um código gerado (ex.: `RSV-3021`) ou de um valor | Gerei códigos só com letras para eliminar o falso positivo. O enunciado não avisa |

## Travas

1. **uv ausente** (ambiente). De 13:02 a 13:05, cerca de 3 min. O
   enunciado exige uv, mas a máquina não tinha. Destravado com o instalador
   oficial (`curl -LsSf https://astral.sh/uv/install.sh | sh`). Um aluno que
   seguiu a aula de preparação não teria essa trava.
2. **Confirmação consumida sem executar com SQLite** (ADK). Cerca de 6 min
   para mim, de 13:12 a 13:18, e estimo horas para um aluno.
   - Sintoma: depois de `POST /confirmacoes {"confirmado": true}`, a API
     devolvia 200 com `resposta: ""`, a pendência sumia e o visitante não era
     gravado.
   - Com `InMemorySessionService`, o mesmo código funcionava.
   - Causa, lida no código-fonte:
     - `Runner._find_agent_to_run` só entrega a resposta ao agente que pediu
       a confirmação se o **último** evento da sessão for um function
       response (`find_matching_function_call`).
     - Na memória, o último evento é o `FR:autorizar_visitante`, emitido
       depois do `FC:adk_request_confirmation`.
     - O `SqliteSessionService` lê com `ORDER BY timestamp`, e o FR foi
       criado alguns milissegundos antes do pedido de confirmação. Ao
       recarregar, a ordem se inverte.
     - Com isso, o Runner varre os agentes transferíveis. Meus especialistas
       tinham `disallow_transfer_to_parent=True`, então a varredura cai no
       agente principal, que não tem a tool, e o scheduler faz
       "fast-forward".
   - Como destravei: um `Runner` próprio que sobrescreve
     `_find_agent_to_run`. A resposta de confirmação vai para o autor do
     pedido, e texto novo vai para o agente principal.
   - Também ativei `ResumabilityConfig(is_resumable=True)`.
   - Fontes lidas: `runners.py`, `flows/llm_flows/request_confirmation.py`,
     `flows/llm_flows/functions.py`,
     `workflow/_dynamic_node_scheduler.py`,
     `workflow/utils/_rehydration_utils.py`,
     `workflow/utils/_replay_interceptor.py` e
     `sessions/sqlite_session_service.py`.
3. **Especialista "gruda" na conversa** (modelo/ADK). Cerca de 4 min.
   - Com sub-agentes transferíveis (o padrão), a mensagem seguinte vai para o
     último especialista.
   - O `especialista_reservas` recusou "Libera a entrada da Joana…" e "Até
     que horas a piscina…" em vez de transferir de volta. Isso aconteceu com
     `gemini-2.5-flash-lite`.
   - Destravado com `disallow_transfer_to_parent/peers`, e isso causou a
     trava 2.
4. **Resposta vazia do modelo depois de erro de tool** (modelo,
   `gemini-2.5-flash-lite`). No passo 10, o modelo devolveu conteúdo vazio
   depois de "data ocupada". Destravado com um fallback na API (usa a
   mensagem da última tool) e com a troca para `gemini-3.1-flash-lite`.
5. **Modelo não chama a tool de novo depois de uma negação** (modelo). No
   passo 8, o agente principal respondeu pelo histórico ("já foi solicitada e
   aguarda confirmação") sem transferir. Destravado reforçando no prompt que
   cada pedido novo passa de novo pelas tools e que o principal nunca
   responde reservas nem visitantes sozinho.
6. **Pequena, minha:** `pkill -f "uvicorn aurora.api"` matou o próprio
   shell. Troquei por controle por porta/PID.

Não houve erro de cota (nenhum 429 ou RESOURCE_EXHAUSTED nos logs).

## Pesquisa

- **Código-fonte do ADK 2.2.0**, dentro do `.venv`:
  - `tools/tool_confirmation.py`
  - `agents/context.py` (`request_confirmation`)
  - `tools/function_tool.py` (`require_confirmation`)
  - `flows/llm_flows/request_confirmation.py`, para descobrir que a
    resposta é um `FunctionResponse` com `name="adk_request_confirmation"`,
    o `id` do pedido e `{"confirmed": bool}`
  - `runners.py` (`_resolve_invocation_id_from_fr`, `_find_agent_to_run`,
    `_run_node_async`)
  - `tools/agent_tool.py`, para confirmar que a AgentTool usa
    `InMemorySessionService` próprio
  - `sessions/sqlite_session_service.py`, `workflow/…`
  - `agents/llm_agent.py` (`mode`)
- **Documentação do Gemini:**
  `https://ai.google.dev/gemini-api/docs/rate-limits` não trouxe números. A
  lista de modelos veio da API `v1beta/models` com a própria chave.
- **Não usei** a página de confirmação de ações da documentação do ADK nem o
  `adk web`. Fui direto ao código-fonte, que a pista do enunciado também
  cita. O conteúdo das aulas listadas cobriria AgentTool, transferência,
  state e Runner. O que ficou além delas foi a mecânica da resposta de
  confirmação numa API própria (o enunciado avisa) e o comportamento do
  runtime de nós do ADK 2.x na retomada (o enunciado não avisa).

## Decisões

| Decisão | Motivo | Alternativas descartadas |
|---|---|---|
| ADK 2.2.0 exato | É a versão do curso, e o enunciado diz que foi testada com SQLite | 2.9.1: mais risco, e a dica pede para testar cedo |
| `SqliteSessionService` (aiosqlite) + SQLite para o condomínio | Sem serviço externo e sem SQLAlchemy, com um comando só para subir | Postgres em container; `DatabaseSessionService` (exige extra `sqlalchemy`) |
| Confirmação pelo mecanismo do ADK (`request_confirmation` dentro da tool) | É o conceito que o requisito pede. Na aprovação, o ADK reexecuta a chamada **original**, e o modelo não troca os argumentos | Tabela própria de pendências com execução direta na rota (ver Atalhos); `FunctionTool(require_confirmation=callable)`, que não me deixava checar a disponibilidade antes nem montar `detalhes` |
| Pendências derivadas dos eventos (FC `adk_request_confirmation` sem FR do usuário) | Persistem junto com a sessão (G3), e o 409 para id repetido sai de graça | Guardar pendências no state ou em outra tabela |
| `asyncio.Lock` por sessão | Duas aprovações simultâneas do mesmo id não passam juntas pela checagem | Nenhuma trava |
| Apartamento só no state, nenhuma tool com parâmetro de apartamento | O modelo não tem como expressar "outro apartamento" | Parâmetro `apartamento` validado contra o state |
| Mesma mensagem para "código inexistente" e "de outro apartamento" | Não confirma que o código existe | Mensagens diferentes |
| Regulamento via AgentTool + busca por palavras-chave (até 3 artigos) | Os artigos ficam na sessão descartável da AgentTool, e a busca reduz tokens | Tool no principal devolvendo artigos (eles entrariam nos eventos); especialista com o regulamento inteiro na instrução (caro); sub-agente com transferência (a leitura entraria nos eventos) |
| Especialistas sem transferência de volta + `AuroraRunner` | Roteamento determinístico: texto novo vai para o principal, confirmação para quem pediu | Confiar no modelo para transferir de volta (falhou); sub-agentes em modo `task` (runtime novo e pouco documentado) |
| `ResumabilityConfig(is_resumable=True)` | Retomada baseada nos eventos persistidos | Não resumível. Com o Runner próprio talvez funcionasse, mas não testei |
| Códigos `RSV-` + 6 letras, reservas canceladas mantidas (`cancelada=1`) | Nunca repete e nunca contém "302" | Hex, UUID ou sequencial |
| `gemini-3.1-flash-lite` em todos os agentes | Roteou melhor que o 2.5-flash-lite, é barato e está disponível na chave | `gemini-2.5-flash` (mais caro); modelos `preview` (limites menores) |
| Fallback de `resposta` com a mensagem da última tool | O modelo às vezes encerra sem texto | Devolver string vazia |

## Onde o enunciado decidiu por você

- **Pista da Garantia 4** ("pense em onde a leitura do regulamento acontece e
  no que dessa leitura volta para a conversa"): praticamente entrega a
  solução "isolar a leitura num agente/AgentTool e devolver só a resposta".
- **Segunda pista da Garantia 1** ("o framework não ignora sozinho uma
  resposta repetida"): entrega que o controle de pendências e o 409 são
  responsabilidade do aluno. É útil, mas tira a descoberta.
- **Garantia 2**, "o que chega à conversa é só se a data está livre ou
  ocupada, nunca de quem é a reserva": define o formato de retorno da tool.
- **Dica final sobre SQLite + 2.2.0**: empurra a versão e o armazenamento.
- **Dicas de `.env` e `app_name`**: evitam duas travas clássicas. Isso é bom,
  mas são exatamente os tropeços que a aula de Runner deveria ensinar.
- **As mensagens exatas do fluxo** permitem ajustar prompts para aquelas
  frases. "O avaliador pode variar a redação" mitiga, mas pouco.

## Onde faltou orientação

- **Roteamento da retomada no ADK 2.x.** Uma linha como "a resposta da
  confirmação precisa chegar ao agente que tem a tool; confira quem o Runner
  escolhe para continuar a sessão" teria poupado a trava 2 sem entregar a
  solução. A dica atual ("conferimos… funcionando com SQLite") induz a achar
  que qualquer topologia funciona.
- **Limites do plano gratuito.** A documentação não lista mais os números.
  Faltou dizer "veja em aistudio.google.com/rate-limit" e uma estimativa de
  quantas chamadas o fluxo do avaliador consome (aqui, ~30).
- **Semântica da restauração** (inclui ou não as sessões).
- **Se AgentTool conta como especialista.**
- **Formato esperado de `GET /eventos`.**
- **Operacionalização de "trechos sem relação"**: tamanho do trecho e se
  artigos do mesmo capítulo contam.
- **Checagem por substring `302`**: avisar que códigos e textos gerados podem
  conter "302" por acaso.
- **Passo 3**: dizer que a checagem dos eventos deve ser feita antes do
  passo 4.
- **Link do repositório base** ainda é placeholder.

## Custo

- **Modelos:** `gemini-3.1-flash-lite` em todos os agentes, incluindo o
  especialista de regulamento. Testei `gemini-2.5-flash-lite` antes e
  descartei (trava 4). A lista de modelos disponíveis veio de `GET
  v1beta/models`.
- **Erros de cota:** nenhum 429 ou RESOURCE_EXHAUSTED em nenhum momento
  (checado com grep nos logs; as ocorrências de "429" eram parte do caminho
  da pasta temporária). O cabeçalho de resposta do Gemini mostrou
  `x-gemini-service-tier: standard`. Não consigo confirmar do meu lado se a
  chave é do plano gratuito ou pago.
- **Chamadas ao modelo (estimativa):**
  - Desenvolvimento: ~110 chamadas.
    - 4 sondagens diretas por curl.
    - Testes manuais dos passos 3 a 12 com 2.5-flash-lite: ~25.
    - Duas rodadas completas do fluxo de desenvolvimento, com e sem a
      correção: ~60.
    - Três execuções do script de depuração da retomada: ~9.
    - Testes pontuais de confirmação: ~6.
    - Passo 13 de desenvolvimento: ~3.
  - Fluxo do avaliador: ~30 chamadas.
    - S1 até o passo 12: 21 respostas do modelo nos eventos.
    - 2 chamadas dentro da AgentTool.
    - S2: ~2.
    - Passo 13: ~3.
  - Tokens por chamada são baixos: instruções de ~1,5 mil caracteres, sem
    regulamento no contexto. A AgentTool recebe no máximo 3 artigos.

## Atalhos

- **Garantia 1 sem o mecanismo do ADK.** Guardar pendências numa tabela
  própria e executar a ação direto na rota `/confirmacoes`, sem retomar o
  agente, passa em todos os critérios dos passos 7, 8, 9 e 11 e é bem mais
  simples. O fluxo não verifica que a confirmação passou pelo ADK nem que a
  execução usou os argumentos originais da chamada.
- **Garantia 4 cara.** Um especialista via AgentTool com o **regulamento
  inteiro na instrução** passa em todos os critérios: o principal não tem o
  regulamento e os eventos não têm trechos. Isso contraria o espírito
  declarado ("cada chamada ao modelo fica mais cara"), porque cada dúvida
  custa cerca de 12 mil tokens.
- **Garantia 2 só por prompt.** Tools com parâmetro `apartamento` e uma
  instrução "nunca use outro apartamento" provavelmente passam nos passos 3,
  4 e 10 com um modelo obediente. O fluxo não tenta nenhuma injeção mais
  elaborada, então não distingue regra no código de regra no prompt.
- **Código de reserva reaproveitado.** O passo 13 só confere repetição entre
  códigos ativos. Uma solução que apaga a RSV-1377 e depois gera outra
  reserva com o mesmo código passaria.
- **Ajuste de prompt às frases do fluxo.** As mensagens são conhecidas de
  antemão.
- **Na minha própria solução:**
  - `AuroraRunner` sobrescreve um método privado do ADK
    (`_find_agent_to_run`). Funciona na 2.2.0, fixada, mas é frágil numa
    atualização.
  - O fallback de `resposta` usa a mensagem da tool quando o modelo fica
    mudo. Não fura regra nenhuma, mas mascara uma falha do modelo.

## Notas

- **Clareza: 7/10.** O enunciado é bem estruturado e o contrato é preciso,
  mas a checagem do passo 3 é quebrada pelo passo 4, há um link
  placeholder, a instrução de consultar limites não se cumpre com a
  documentação atual e vários comportamentos de borda ficaram em aberto
  (restauração, 404/422, formato dos eventos).
- **Desafio: 8/10.** As garantias 2, 3 e 4 saem com os conceitos do curso,
  mas a Garantia 1 numa API própria, somada à retomada no runtime de nós do
  ADK 2.x com SQLite, exige ler bastante código-fonte e tem uma armadilha
  silenciosa (200 sem executar) que o enunciado não sinaliza.
