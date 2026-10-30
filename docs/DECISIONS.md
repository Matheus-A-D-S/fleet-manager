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
