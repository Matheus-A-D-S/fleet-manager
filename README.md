# FleetTrack — gestão de frota e rastreamento logístico

[![CI](https://github.com/Matheus-A-D-S/fleet-manager/actions/workflows/ci.yml/badge.svg)](https://github.com/Matheus-A-D-S/fleet-manager/actions/workflows/ci.yml)

Plataforma **multi-empresa (SaaS)** para acompanhar veículos, motoristas e viagens em tempo real, com alertas por e-mail e trilha de auditoria. Cada empresa enxerga apenas os próprios dados.

| Camada | Tecnologia |
|---|---|
| Back-end | Python 3.12, Django 5, Django REST Framework, Django Channels |
| Banco de dados | PostgreSQL 16 |
| Mensageria e tempo real | Celery + Redis (tarefas), WebSocket via Channels |
| Autenticação | JWT (SimpleJWT), refresh rotativo, verificação de e-mail, reset de senha |
| Front-end | React 18, Vite, React Router, Leaflet |
| Qualidade | pytest (+ cobertura), ruff, GitHub Actions, pre-commit |
| Operação | Docker Compose (dev e prod), Nginx, logs JSON, health checks, Sentry opcional |

Arquitetura e diagramas: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) · Decisões e trade-offs: [`docs/DECISIONS.md`](docs/DECISIONS.md)

## Funcionalidades

- **Frota:** veículos, motoristas (CNH, vínculo com usuário), manutenções, vencimentos de seguro e licenciamento.
- **Viagens:** máquina de estados (planejada → em andamento → concluída/cancelada) que atualiza a situação do veículo.
- **Rastreamento:** GPS enviado pelo motorista ou por rastreador; mapa **ao vivo via WebSocket** (com fallback para polling) e trajeto da viagem.
- **Alertas por e-mail:** excesso de velocidade, manutenção (data ou km), documentos vencendo, viagem atrasada; sem e-mails repetidos.
- **Auditoria:** quem criou, alterou (campo a campo) ou excluiu o quê, com IP e id de correlação.
- **Multi-empresa:** cada empresa tem seus usuários, frota, viagens, alertas e auditoria isolados; o mapa em tempo real e os e-mails também são separados por empresa.
- **Equipe:** o administrador convida usuários por e-mail (o convidado define a própria senha), altera perfis e desativa acessos.
- **Perfis:** administrador, gestor e motorista (o motorista só vê e opera as próprias viagens).

## Como rodar

```bash
docker compose up --build                                   # sobe tudo
docker compose exec backend python manage.py seed_demo      # dados de exemplo
docker compose exec backend python manage.py simulate_gps --speeding   # GPS simulado (deixe rodando)
```

| Serviço | URL |
|---|---|
| Aplicação | http://localhost:5173 |
| API / Swagger | http://localhost:8000/api/docs/ |
| Admin Django | http://localhost:8000/admin/ |
| Caixa de e-mail (MailHog) | http://localhost:8025 |

O `seed_demo` cria **duas empresas** para você ver o isolamento (somente dev):

| Empresa | Login | Senha |
|---|---|---|
| Transportes Alfa (administrador) | `gestor@alfa.local` | `Gestor@12345` |
| Transportes Alfa (motorista) | `motorista@alfa.local` | `Motorista@12345` |
| Logística Beta (administrador) | `gestor@beta.local` | `Gestor@12345` |

Entre com cada gestor em uma janela anônima: cada um vê só a própria frota. Contas novas criadas em **Criar conta** nascem como administradoras de uma empresa nova.

Abra **Mapa ao vivo** com o `simulate_gps` rodando: o veículo se move sozinho e, com `--speeding`, gera alertas de velocidade (e e-mails no MailHog).

> **Migrações:** na primeira subida o backend gera as migrações em `backend/apps/*/migrations/`. **Versione-as no Git** (a CI e a produção dependem delas).

Atalhos (`make up`, `make test`, `make lint`...): veja o `Makefile` (no Windows, use WSL/Git Bash ou copie os comandos).

## Testes e qualidade

```bash
docker compose exec backend pytest --cov --cov-report=term-missing
docker compose exec backend ruff check .
```

A suíte cobre autenticação (cadastro com empresa, verificação, reset, logout), permissões por perfil, **isolamento entre empresas** (dados, relações, alertas, e-mails, auditoria e WebSocket), convites de usuários, ciclo da viagem, GPS, regras de alerta e deduplicação, auditoria e health checks. A CI roda lint, verificação de migrações, testes (com PostgreSQL real) e o build das imagens a cada push.

Para formatar o código uma vez e ativar os hooks: `pip install pre-commit && pre-commit install && pre-commit run --all-files`.

## Produção (referência)

```bash
cp .env.prod.example .env.prod      # preencha segredos, domínio e SMTP
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Nginx serve o React e faz proxy de `/api`, `/admin` e `/ws`; o backend roda em Daphne como usuário sem root; migrações rodam em serviço próprio; há health checks (`/api/health/` e `/api/health/ready/`) e logs em JSON com `X-Request-ID`. Para HTTPS, coloque um balanceador/Caddy/Cloudflare na frente e use `DJANGO_HTTPS=1`.

## Endpoints principais

`/api/auth/…` (incl. `users/` e `users/{id}/resend-invite/`) · `/api/fleet/{vehicles,drivers,maintenance}/` · `/api/logistics/trips/` (+ `start`, `complete`, `cancel`, `track`) · `/api/logistics/{pings,live,dashboard}/` · `/api/alerts/` (+ `resolve`, `scan`) · `/api/audit/` · `ws://…/ws/fleet/?token=<access>`

## Estrutura

```
backend/   Django (apps: accounts [empresas e usuários], fleet, logistics, alerts, audit, core) + tests/
frontend/  React + Vite (+ Dockerfile.prod e nginx.conf)
docs/      arquitetura e decisões
.github/   CI
```

## Roadmap

Cercas geográficas com PostGIS, planos/limites por empresa, 2FA, row-level security no PostgreSQL, PWA do motorista, rastreio público para o cliente final, custos de combustível/manutenção, métricas Prometheus.
