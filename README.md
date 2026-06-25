# Code Buddy

Agente de IA que revisa Pull Requests de GitHub de forma automática: 
- analiza los cambios
- detecta bugs, errores de sintaxis y malas prácticas
- genera tests unitarios para el código revisado
- publica los resultados como comentarios directamente en el PR.

---

## Requisitos previos

- Cuenta de AWS
- [AWS CLI](https://aws.amazon.com/cli/)
- [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- [AgentCore CLI](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-cli.html)
- Python 3.12
- Docker instalado o acceso a AWS CloudShell
- Cuenta de GitHub con un repositorio donde probar el agente

---

## Despliegue

### 1. Configuración previa

**En GitHub:** Profile → Settings → Developer Settings → Personal access tokens → Tokens (classic) → Generate new token (classic) → seleccionar scope `repo`.

Copia el token (empieza por `ghp_`).

**En AWS Secrets Manager:** Store a new secret → Other type of secret:
- Key: `access_token`
- Value: `ghp_...` (el PAT de GitHub)

Copia el ARN del secreto.

---

### 2. Desplegar el agente (desde AWS CloudShell)

Abre CloudShell en la consola AWS, sube la carpeta `agent/` como zip (Actions → Upload file), descomprímela e instala dependencias:

```bash
unzip agent.zip && cd agent
pip install bedrock-agentcore-starter-toolkit
```

Ejecuta los tres comandos en orden:

```bash
# Crea el AgentCore Gateway con el target de GitHub
python deploy.py --region eu-west-1 setup-gateway \
  --github-token-secret-arn PEGA_TU_ARN

# Configura el runtime (genera .bedrock_agentcore.yaml)
python deploy.py --region eu-west-1 configure \
  --oauth-secret-arn PEGA_TU_ARN \
  --non-interactive

# Construye la imagen Docker, la sube a ECR y crea el AgentCore Runtime
OAUTH_SECRET_ARN=PEGA_TU_ARN python deploy.py --region eu-west-1 deploy
```

Al terminar el deploy obtendrás el `AgentRuntimeArn`. Cópialo.

---

### 3. Desplegar la infraestructura SAM (desde terminal local)

Edita `milestones/v5-agentcore/samconfig.toml` y rellena:
- `AgentRuntimeArn` → el ARN del paso anterior
- `GitHubWebhookSecret` → una contraseña que usarás en el webhook

```bash
cd milestones/v5-agentcore
sam build
sam deploy --config-env dev
```

El output del deploy incluye el `WebhookUrl`. Cópialo.

---

### 4. Configurar el webhook en GitHub

GitHub → Settings → Webhooks → Add webhook:
- **Payload URL:** la `WebhookUrl` del output
- **Content type:** `application/json`
- **Secret:** el valor de `GitHubWebhookSecret`
- **SSL verification:** habilitada
- **Events:** Pull requests

---

## Verificación

1. Abre un PR en GitHub con cualquier cambio de código
2. **CloudWatch** → `/aws/lambda/code-buddy-webhook-handler-v5-dev` → debe aparecer `PR_ENQUEUED`
3. **CloudWatch** → `/aws/lambda/code-buddy-pr-processor-v5-dev` → debe aparecer `PR_EVENT_RECEIVED`
4. **CloudWatch** → `/aws/bedrock-agentcore/runtimes/app-...-DEFAULT` → debe aparecer `INVOCATION_COMPLETE`
5. **GitHub** → en el PR verás:
   - Comentarios inline del agente sobre el código
   - Una rama nueva `code-buddy/tests-pr-{N}` creada
   - Un fichero `tests/test_pr_changes.py` en esa rama con tests unitarios generados y ejecutados

---

## Cómo funciona

```
GitHub
      │ webhook POST /webhook
      ▼
API Gateway HTTP (SAM)
      │
      ▼
Lambda webhook_handler  →  valida HMAC-SHA256  →  SQS
                                                     │
                                          Lambda pr_event_processor
                                                     │
                                          invoke_agent_runtime()
                                                     │
                                    ┌────────────────▼────────────────┐
                                    │       AgentCore Runtime         │
                                    │       (Docker ARM64)            │
                                    │                                 │
                                    │  Strands Agent + Claude Sonnet  │
                                    │                                 │
                                    │  Tools (GET vía Gateway MCP):   │
                                    │  • get_pull_request             │
                                    │  • list_pull_request_files      │
                                    │                                 │
                                    │  Tools (POST directo a GitHub): │
                                    │  • create_review_comment        │
                                    │  • submit_pull_request_review   │
                                    │  • create_branch                │
                                    │  • create_file                  │
                                    │                                 │
                                    │  • code_interpreter (sandbox)   │
                                    └─────────────────────────────────┘
                                                     │
                                    GitHub (comentarios + rama de tests)
```

---

## Estructura del proyecto

```
code_budy/
├── agent/                          ← AgentCore Runtime (contenedor Strands)
│   ├── app.py                      ← BedrockAgentCoreApp + @app.entrypoint
│   ├── config.py                   ← settings, system prompt, model ID
│   ├── deploy.py                   ← setup-gateway / configure / deploy
│   ├── gateway_setup.py            ← crea el Gateway MCP con target GitHub
│   ├── tools/
│   │   └── github_write_tools.py  ← create_review_comment, submit_review,
│   │                                  create_branch, create_file
│   ├── requirements.txt
│   ├── Dockerfile                  ← linux/arm64, puerto 8080
│   └── gateway_config.json         ← generado por gateway_setup.py
│
├── milestones/
│   ├── v1-webhook-logger/          ← recibe y loguea webhooks
│   ├── v2-webhook-handler/         ← valida firma HMAC-SHA256
│   ├── v3-webhook-sqs/             ← encola eventos en SQS
│   ├── v4-pr-processor/            ← procesa eventos PR (simulado)
│   └── v5-agentcore/               ← stack completo con AgentCore Runtime
│       ├── template.yaml
│       ├── samconfig.toml
│       └── src/
│           ├── webhook_handler.py
│           └── pr_event_processor.py
│
└── sam/                            ← stack SAM completo (prod)
    ├── template.yaml
    ├── samconfig.toml
    └── src/
        ├── webhook_handler/
        ├── pr_event_processor/
        └── secret_rotation/
```

---

## Variables de entorno del agente

| Variable | Descripción |
|---|---|
| `BEDROCK_MODEL_ID` | ID del modelo Claude Sonnet |
| `OAUTH_SECRET_ARN` | ARN del secreto con el PAT de GitHub en Secrets Manager |
| `PROMPT_VERSION_ARN` | ARN del prompt en Bedrock Prompt Management (opcional) |
| `AWS_REGION` | Región AWS |
| `ENVIRONMENT` | dev / staging / prod |
