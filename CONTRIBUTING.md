# Guia de Contribuição

## 📋 Antes de começar

1. Faça fork do repositório
2. Crie uma branch para sua feature: `git checkout -b feature/sua-feature`
3. Siga as convenções de código abaixo
4. Faça commit com mensagens descritivas
5. Abra um Pull Request

## 🎨 Convenções de Código

### Python
- Use **PEP 8** como padrão
- Máximo 127 caracteres por linha
- Use type hints em funções
- Docstrings em português

### Commits
```
feat: adicionar nova funcionalidade
fix: corrigir bug
docs: atualizar documentação
test: adicionar testes
refactor: refatorar código
chore: tarefas de manutenção
```

### Branches
- `main` - Produção (protegida)
- `develop` - Desenvolvimento
- `feature/nome` - Novas features
- `fix/nome` - Correções de bugs

## 🧪 Testes

Antes de fazer commit:
```bash
# Linting
flake8 app scripts

# Testes
pytest

# Cobertura
pytest --cov=app
```

## 🔐 Segurança

- ❌ Nunca commitar `.env` com credenciais reais
- ✅ Usar `.env.example` como template
- ✅ Revisar logs antes de commitar
- ✅ Validar entrada de usuários

## 📝 Documentação

- Atualizar README.md se necessário
- Adicionar docstrings em novas funções
- Documentar endpoints novos
- Incluir exemplos de uso

## 🚀 Deploy

1. Criar PR para `develop`
2. Passar em todos os testes (CI)
3. Fazer review
4. Merge para `develop`
5. Quando pronto, merge `develop` → `main`
6. GitHub Actions faz deploy automático

## 📞 Dúvidas?

Abra uma issue ou entre em contato!
