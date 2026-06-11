# Servidor WhatsApp Meta API

Este projeto implementa uma API persistente para integração com a **WhatsApp Cloud API** da Meta. A estrutura foi criada para operar em servidor sempre ligado, receber webhooks, guardar eventos, consultar números, enviar mensagens autorizadas, listar templates e executar diagnóstico técnico sem depender do navegador Chrome.

## Estado atual

A base técnica está preparada para funcionar localmente no servidor. Antes de publicar o endpoint na internet e ligar à Meta, ainda é necessário configurar credenciais reais no arquivo `.env` e definir domínio/HTTPS.

| Área | Estado |
|---|---|
| API FastAPI | Criada |
| Banco SQLite de logs | Criado automaticamente no arranque |
| Webhook GET de verificação Meta | Criado em `/webhook` |
| Webhook POST de receção de eventos | Criado em `/webhook` |
| Validação de assinatura Meta | Suportada se `META_APP_SECRET` for configurado |
| Endpoints de números WhatsApp | Criados |
| Registro de número Cloud API | Criado em `/phone-number/register` |
| Envio de mensagem de texto | Criado em `/messages/text` |
| Envio de template | Criado em `/messages/template` |
| Logs administrativos | Criados em `/events` e `/actions` |

## Variáveis necessárias

Copie `.env.example` para `.env` e preencha os valores reais.

| Variável | Função |
|---|---|
| `API_ADMIN_TOKEN` | Token interno para proteger endpoints administrativos da API própria. |
| `META_VERIFY_TOKEN` | Token usado pela Meta para validar o webhook. |
| `META_APP_SECRET` | App Secret da Meta, usado para validar assinatura dos webhooks. |
| `META_ACCESS_TOKEN` | Token de usuário do sistema com permissões WhatsApp. |
| `DEFAULT_WABA_ID` | ID padrão da WhatsApp Business Account. |
| `DEFAULT_PHONE_NUMBER_ID` | ID padrão do número remetente. |

## Endpoints principais

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/health` | Verifica se a API está online e quais credenciais estão configuradas. |
| `GET` | `/webhook` | Endpoint usado pela Meta para validar o webhook. |
| `POST` | `/webhook` | Recebe mensagens, status e alertas enviados pela Meta. |
| `GET` | `/events` | Lista eventos de webhook recebidos. Requer `Authorization: Bearer <API_ADMIN_TOKEN>`. |
| `GET` | `/actions` | Lista chamadas feitas pela API para a Graph API. Requer token administrativo. |
| `GET` | `/waba/{waba_id}/phone-numbers` | Consulta números de uma WABA. |
| `GET` | `/phone-number/{phone_number_id}` | Consulta detalhes de um número. |
| `POST` | `/phone-number/register` | Registra/conecta número na Cloud API usando PIN de duas etapas. |
| `POST` | `/messages/text` | Envia mensagem de texto dentro das regras da WhatsApp Cloud API. |
| `POST` | `/messages/template` | Envia mensagem por template aprovado. |
| `GET` | `/waba/{waba_id}/message-templates` | Lista templates da WABA. |
| `GET` | `/diagnostics` | Executa diagnóstico dos IDs padrão configurados. |

## Execução local

```bash
cd /home/ubuntu/whatsapp-api-server
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Serviço permanente

O serviço systemd recomendado chama-se `whatsapp-api.service`. Ele deve executar o Uvicorn em `127.0.0.1:8000` e ser colocado atrás de Nginx com HTTPS antes de ligar à Meta em produção.

## Observações de segurança

A API não deve ser exposta diretamente na internet sem HTTPS, firewall e autenticação administrativa. Para webhook público da Meta, use domínio com certificado SSL, Nginx como proxy reverso e mantenha os endpoints administrativos protegidos por token forte.

## Meta Ads, campanhas e diagnóstico

A API agora também possui endpoints administrativos para **Meta Ads**. A camada foi projetada para leitura, diagnóstico e pré-visualização segura antes de qualquer alteração real. Por padrão, a criação ou alteração de campanhas fica bloqueada por `META_ADS_WRITE_ENABLED=false`.

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/meta/config` | Lista Business IDs e contas de anúncio configurados localmente, sem expor credenciais. |
| `GET` | `/meta/business/{business_id}/ad-accounts` | Lista contas de anúncios de um Business Manager. |
| `GET` | `/meta/ad-account/{ad_account_id}` | Consulta detalhes de uma conta de anúncios. |
| `GET` | `/meta/ad-account/{ad_account_id}/campaigns` | Lista campanhas da conta de anúncios. |
| `GET` | `/meta/campaign/{campaign_id}` | Consulta detalhes de uma campanha. |
| `GET` | `/meta/ad-account/{ad_account_id}/adsets` | Lista conjuntos de anúncios. |
| `GET` | `/meta/adset/{adset_id}` | Consulta detalhes de um conjunto. |
| `GET` | `/meta/ad-account/{ad_account_id}/ads` | Lista anúncios. |
| `GET` | `/meta/ad/{ad_id}` | Consulta detalhes de um anúncio. |
| `GET` | `/meta/ad-account/{ad_account_id}/insights` | Consulta métricas de performance. |
| `GET` | `/meta/ad-account/{ad_account_id}/diagnostics` | Executa diagnóstico técnico da conta. |
| `GET` | `/meta/diagnostics` | Executa diagnóstico dos ativos configurados no `.env`. |
| `GET` | `/meta/campaign-templates` | Mostra modelos técnicos de criação e estado das travas. |
| `POST` | `/meta/ad-account/{ad_account_id}/campaigns/preview` | Gera pré-visualização de payload de criação sem executar alteração real. |
| `POST` | `/meta/ad-account/{ad_account_id}/campaigns/create` | Cria campanha apenas quando a trava global e a confirmação explícita estão corretas. |
| `POST` | `/meta/campaign/{campaign_id}/status/preview` | Pré-visualiza alteração de status sem executar. |
| `POST` | `/meta/campaign/{campaign_id}/status` | Altera status apenas com trava global e confirmação explícita. |
| `POST` | `/meta/write-preview/{path}` | Pré-visualiza operação POST genérica na Graph API. |
| `POST` | `/meta/write/{path}` | Executa POST genérico apenas com autorização explícita. |

## Variáveis Meta Ads

| Variável | Função |
|---|---|
| `DEFAULT_META_BUSINESS_IDS` | Lista de Business IDs/portfólios Meta a diagnosticar por padrão. |
| `DEFAULT_AD_ACCOUNT_IDS` | Lista opcional de contas de anúncio para diagnóstico direto. |
| `META_ADS_WRITE_ENABLED` | Trava global para qualquer escrita em campanhas. Deve permanecer `false` até confirmação explícita. |
| `META_ADS_WRITE_CONFIRMATION_PHRASE` | Frase que precisa ser enviada no payload de escrita. Valor atual recomendado: `CONFIRMO ALTERAR META ADS`. |
| `REQUIRE_EXPLICIT_USER_CONFIRMATION` | Registro operacional de que ações reais exigem confirmação explícita. |

## Monitoramento e relatórios

O servidor possui rotinas recorrentes no cron do usuário `ubuntu`. A verificação de saúde roda a cada 5 minutos com timeout otimizado (5 segundos), rotação automática de logs e detecção de falhas consecutivas. O relatório operacional diário roda às 09:00 UTC e grava o relatório mais recente em `reports/latest_operational_report.md`, além de snapshots JSON em `reports/operational_report_*.json`.

### Healthcheck Otimizado

- **Frequência:** A cada 5 minutos (`*/5 * * * *`)
- **Timeout:** 5 segundos (reduzido de 10 para melhor responsividade)
- **Logs:** `logs/healthcheck_events.log` (rotação automática em 5MB)
- **Métricas:** `logs/healthcheck_metrics.json` (histórico em JSON para análise)
- **Reinicialização:** Automática apenas após 2+ falhas consecutivas
- **Comportamento:** Não reinicia em falha isolada; aguarda padrão de falha

| Rotina | Frequência | Comando |
|---|---|---|
| Healthcheck | A cada 5 minutos | `/home/ubuntu/whatsapp-api-server/scripts/healthcheck.sh` |
| Relatório operacional | Diariamente às 09:00 UTC | `cd /home/ubuntu/whatsapp-api-server && .venv/bin/python scripts/generate_report.py` |

## Atualizar Crontab

Para atualizar o cronograma de healthcheck (ex: mudar frequência), execute:

```bash
bash /home/ubuntu/whatsapp-api-server/scripts/update_cron.sh
```

Este script remove jobs antigos e instala a nova configuração.

## Fluxo seguro para subir campanhas

Antes de subir qualquer campanha real, gere uma pré-visualização com `/meta/ad-account/{ad_account_id}/campaigns/preview` e revise objetivo, orçamento, status, categoria especial e conta de anúncios. A criação real só deve ser habilitada depois de confirmação explícita do usuário, configuração de `META_ADS_WRITE_ENABLED=true`, token Meta com permissão adequada e envio do campo `confirmation_text` com a frase configurada. Por segurança, campanhas criadas por modelo devem iniciar em `PAUSED`, salvo decisão operacional expressa em contrário.
