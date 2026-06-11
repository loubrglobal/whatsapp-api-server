# WhatsApp API Server - Guia de Deployment

## 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Requisitos](#requisitos)
3. [Instalação Local](#instalação-local)
4. [Deployment em Servidor Persistente](#deployment-em-servidor-persistente)
5. [Configuração de Produção](#configuração-de-produção)
6. [GitHub Actions CI/CD](#github-actions-cicd)
7. [Monitoramento](#monitoramento)
8. [Troubleshooting](#troubleshooting)

## 🎯 Visão Geral

Este é um servidor FastAPI persistente para integração com:
- **WhatsApp Cloud API** - Recebimento de webhooks, envio de mensagens
- **Meta Ads API** - Leitura de campanhas, diagnóstico, pré-visualização segura

**Características principais:**
- ✅ Travas de escrita por padrão (segurança)
- ✅ Pré-visualização de operações antes de executar
- ✅ Healthcheck automático a cada 5 minutos
- ✅ Relatórios operacionais diários
- ✅ Logs estruturados em JSON
- ✅ Integração com GitHub Actions

## 📦 Requisitos

### Sistema
- Ubuntu 20.04+ ou similar
- Python 3.11+
- Acesso root/sudo
- Porta 8000 disponível (ou configurável)

### Credenciais
- Token de acesso Meta (WhatsApp + Ads)
- Business Account ID (WABA)
- Phone Number ID
- App Secret (para validação de webhook)

## 🚀 Instalação Local

### 1. Clonar repositório
```bash
git clone https://github.com/loubrglobal/whatsapp-api-server.git
cd whatsapp-api-server
```

### 2. Criar ambiente virtual
```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. Instalar dependências
```bash
pip install -r requirements.txt
```

### 4. Configurar variáveis de ambiente
```bash
cp .env.example .env
# Editar .env com suas credenciais
nano .env
```

### 5. Executar servidor localmente
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Acesse: http://localhost:8000/docs (Swagger UI)

## 🖥️ Deployment em Servidor Persistente

### 1. Preparar servidor
```bash
# SSH no servidor
ssh ubuntu@seu-servidor

# Clonar repositório
git clone https://github.com/loubrglobal/whatsapp-api-server.git
cd whatsapp-api-server

# Criar ambiente virtual
python3.11 -m venv .venv
source .venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 2. Configurar systemd service
```bash
# Copiar arquivo de serviço
sudo cp whatsapp-api.service /etc/systemd/system/

# Editar se necessário
sudo nano /etc/systemd/system/whatsapp-api.service

# Recarregar systemd
sudo systemctl daemon-reload

# Habilitar e iniciar serviço
sudo systemctl enable whatsapp-api
sudo systemctl start whatsapp-api

# Verificar status
sudo systemctl status whatsapp-api
```

### 3. Configurar firewall
```bash
# Abrir porta 8000 (apenas para localhost por segurança)
sudo ufw allow 8000/tcp

# Ou com Nginx como proxy reverso (recomendado)
sudo apt install nginx
# Configurar Nginx para proxy reverso na porta 80/443
```

### 4. Configurar healthcheck automático
```bash
# Atualizar crontab
bash scripts/update_cron.sh

# Verificar cron instalado
crontab -l
```

## ⚙️ Configuração de Produção

### 1. Variáveis de ambiente essenciais
```bash
# WhatsApp
META_ACCESS_TOKEN=seu_token_aqui
DEFAULT_WABA_ID=seu_waba_id
DEFAULT_PHONE_NUMBER_ID=seu_phone_id
META_VERIFY_TOKEN=seu_verify_token
META_APP_SECRET=seu_app_secret

# Meta Ads
DEFAULT_META_BUSINESS_IDS=id1,id2,id3
META_ADS_WRITE_ENABLED=false  # SEMPRE false por padrão!

# Segurança
API_ADMIN_TOKEN=token_forte_aleatorio_aqui
```

### 2. HTTPS com Let's Encrypt
```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-nginx

# Gerar certificado
sudo certbot certonly --nginx -d seu-dominio.com

# Configurar Nginx para HTTPS
sudo nano /etc/nginx/sites-available/whatsapp-api
```

### 3. Nginx como proxy reverso
```nginx
server {
    listen 80;
    server_name seu-dominio.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name seu-dominio.com;

    ssl_certificate /etc/letsencrypt/live/seu-dominio.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/seu-dominio.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔄 GitHub Actions CI/CD

### Workflows disponíveis

#### 1. CI (ci.yml)
- **Trigger:** Push para main/develop, Pull Requests
- **Ações:**
  - Instala dependências
  - Executa linting (flake8)
  - Roda testes (pytest)
  - Verifica segurança (bandit)

#### 2. Health Check (health-check.yml)
- **Trigger:** A cada 6 horas (agendado)
- **Ações:**
  - Valida estrutura do servidor
  - Verifica arquivos essenciais
  - Confirma configuração

#### 3. Deploy (deploy.yml)
- **Trigger:** Push para main
- **Ações:** Placeholder para deploy automático
- **Próximo passo:** Configurar SSH Secrets

### Configurar Deploy Automático

1. Gerar chave SSH no servidor:
```bash
ssh-keygen -t ed25519 -f deploy_key -N ""
```

2. Adicionar chave pública ao `~/.ssh/authorized_keys` do servidor

3. Adicionar chaves ao GitHub Secrets:
   - `DEPLOY_KEY` (chave privada)
   - `SERVER_IP` (IP do servidor)
   - `SERVER_USER` (usuário SSH)

4. Atualizar `.github/workflows/deploy.yml` com comandos SSH

## 📊 Monitoramento

### Healthcheck
```bash
# Verificar manualmente
curl http://localhost:8000/health

# Ver logs
tail -f logs/healthcheck_events.log
tail -f logs/healthcheck_metrics.json
```

### Relatórios
```bash
# Gerar relatório manual
python scripts/generate_report.py

# Ver relatório mais recente
cat reports/latest_operational_report.md
```

### Logs
```bash
# Logs da aplicação
tail -f logs/app.log

# Logs do healthcheck
tail -f logs/healthcheck_events.log

# Logs do sistema
sudo journalctl -u whatsapp-api -f
```

## 🔧 Troubleshooting

### Serviço não inicia
```bash
# Verificar status
sudo systemctl status whatsapp-api

# Ver logs de erro
sudo journalctl -u whatsapp-api -n 50

# Testar manualmente
cd /home/ubuntu/whatsapp-api-server
source .venv/bin/activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Erro de credenciais
```bash
# Verificar .env
cat .env | grep -E "META_|WABA|PHONE"

# Testar endpoint de diagnóstico
curl -H "Authorization: Bearer seu_token" http://localhost:8000/meta/diagnostics
```

### Webhook não recebendo eventos
```bash
# Verificar webhook URL na Meta
# Deve ser: https://seu-dominio.com/webhook

# Testar webhook localmente
curl -X POST http://localhost:8000/webhook \
  -H "Content-Type: application/json" \
  -d '{"entry":[{"changes":[{"value":{"messages":[{"from":"5511912345678","text":{"body":"test"}}]}}]}]}'
```

### Cron não executando
```bash
# Verificar cron instalado
crontab -l

# Ver logs de cron
grep CRON /var/log/syslog | tail -20

# Reinstalar cron
bash scripts/update_cron.sh
```

## 📝 Endpoints principais

### Healthcheck
```
GET /health
```

### WhatsApp
```
GET /webhook - Validação Meta
POST /webhook - Recebimento de eventos
POST /messages/text - Enviar mensagem
GET /events - Listar eventos recebidos
```

### Meta Ads
```
GET /meta/config - Configuração
GET /meta/ad-account/{id}/campaigns - Listar campanhas
GET /meta/ad-account/{id}/diagnostics - Diagnóstico
POST /meta/ad-account/{id}/campaigns/preview - Pré-visualizar
POST /meta/ad-account/{id}/campaigns/create - Criar (com trava)
```

## 🔐 Segurança

- ✅ Travas de escrita por padrão (`META_ADS_WRITE_ENABLED=false`)
- ✅ Confirmação explícita obrigatória
- ✅ Tokens protegidos em `.env` (não commitados)
- ✅ HTTPS obrigatório em produção
- ✅ Validação de assinatura de webhook
- ✅ Logs auditáveis de todas as operações

## 📞 Suporte

Para problemas ou dúvidas:
1. Verificar logs em `logs/`
2. Consultar relatórios em `reports/`
3. Abrir issue no GitHub
4. Contatar Meta Support para erros de API

---

**Última atualização:** Junho 2026
**Versão:** 1.0.0
**Repositório:** https://github.com/loubrglobal/whatsapp-api-server
