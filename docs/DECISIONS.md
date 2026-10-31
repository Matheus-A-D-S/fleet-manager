# Decisões de arquitetura

Registro curto das escolhas e dos trade-offs.

## ADR-001 — JWT de vida curta + refresh rotativo
**Decisão:** access token de 15 min e refresh de 7 dias, com rotação e blacklist no logout.
**Por quê:** a API é consumida por um SPA (e, no futuro, por apps móveis); tokens evitam sessão no servidor e CSRF.
**Trade-off:** o access token não pode ser revogado antes de expirar; por isso é curto. O refresh fica no `localStorage`, que é exposto a XSS. Para endurecer, mover o refresh para cookie `HttpOnly`.

## ADR-002 — E-mails e varreduras em Celery
**Decisão:** nenhum e-mail é enviado dentro da requisição; tudo passa por tarefas Celery com retry e backoff exponencial.
**Por quê:** SMTP lento ou fora do ar não pode travar nem derrubar a API.
**Detalhe:** o envio é enfileirado com `transaction.on_commit`, para o worker nunca processar um registro que ainda não foi gravado.

## ADR-003 — Um problema, um alerta
**Decisão:** `dedupe_key` única. A chave embute o fato que identifica o problema (ex.: `doc:vehicle:7:insurance_expiry:2026-12-01`).
**Efeito:** a varredura horária não repete e-mail; resolver um alerta não o reabre; renovar o documento (nova data) gera um alerta novo. Excesso de velocidade usa chave por veículo/hora.

## ADR-004 — Tempo real com Channels, polling como fallback
**Decisão:** WebSocket para posições; se cair, o front volta ao polling de 10 s e reconecta com backoff exponencial.
**Por quê:** o mapa fica fluido sem sobrecarregar a API. A falha do canal em tempo real nunca impede a gravação do GPS (`publish_position` captura exceções e registra aviso).

## ADR-005 — Autenticação do WebSocket por query string
**Decisão:** `/ws/fleet/?token=<access>`; o navegador não permite cabeçalhos customizados em WebSocket.
**Trade-off:** URLs podem aparecer em logs de proxy. Mitigação: token de 15 min e conexão aceita só para gestores. Alternativa mais forte: *ticket* de uso único emitido por endpoint autenticado.

## ADR-006 — Auditoria na camada da API
**Decisão:** `AuditedMixin` nos viewsets grava criação, alteração (com diff campo a campo) e exclusão; as transições de viagem também.
**Por quê:** é simples e explícita. **Limite:** alterações feitas fora da API (admin, shell, tarefas) não passam por ela; para cobertura total, usar signals ou triggers.

## ADR-007 — Health checks separados
`/api/health/` (liveness, sem dependências) e `/api/health/ready/` (PostgreSQL + Redis). Assim o orquestrador não reinicia o container só porque uma dependência caiu.

## ADR-008 — Multi-empresa com banco único e `organization_id`
**Decisão:** esquema compartilhado, uma coluna `organization` em todas as tabelas de negócio, isolamento na camada da API (queryset, escrita e relações) e grupos de WebSocket por empresa.
**Por quê:** é o modelo com melhor custo/benefício para começar (uma migração, um pool de conexões, onboarding instantâneo) e é o usado pela maioria dos SaaS B2B.
**Trade-offs:** um erro de código pode vazar dados entre empresas, por isso o isolamento é central e testado (`test_tenancy.py`). Passo seguinte natural: *row-level security* no PostgreSQL como segunda barreira. Alternativas descartadas: um schema ou banco por empresa (isolamento mais forte, porém operação e migrações bem mais caras).
**Detalhes:** objeto de outra empresa responde 404; chaves estrangeiras usam `PROTECT` (uma empresa com dados não pode ser apagada por engano); placa e CNH são únicas *por empresa*.
**Limitação conhecida:** o e-mail é único na plataforma, então cada pessoa pertence a uma empresa. Atender consultores em várias empresas exigiria um modelo de *memberships*.

## ADR-009 — Convite por e-mail em vez de senha criada pelo administrador
**Decisão:** o administrador cadastra nome, e-mail e perfil; o usuário nasce com senha inutilizável e recebe um link para definir a própria senha (mesmo mecanismo, com token de uso único, da redefinição de senha).
**Por quê:** ninguém além do próprio usuário conhece a senha, e definir a senha comprova o controle do e-mail.
**Salvaguardas:** o administrador não pode alterar o próprio perfil nem se desativar (a empresa nunca fica sem administrador); usuários são desativados, não excluídos, preservando a trilha de auditoria; a auditoria de usuários registra só campos explícitos, nunca o hash da senha.
