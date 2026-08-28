# 📖 Manual de Migração phpBB → Discourse

**Guia passo a passo para migrar um forum phpBB para Discourse**

---

## 📋 Índice

1. [Pré-requisitos](#pré-requisitos)
2. [Preparação inicial](#preparação-inicial)
3. [Detecção de versão](#detecção-de-versão)
4. [Instalação e configuração](#instalação-e-configuração)
5. [Execução passo a passo](#execução-passo-a-passo)
6. [Validação e testes](#validação-e-testes)
7. [Troubleshooting](#troubleshooting)
8. [Próximos passos](#próximos-passos)

---

## ✅ Pré-requisitos

### Software necessário

- ✅ **Git** : Para clonar o repositório
- ✅ **Python 3.8+** : Para executar os scripts
- ✅ **Docker & Docker Compose** : Para executar Discourse localmente
- ✅ **MySQL/MariaDB** : Acesso à base de dados phpBB (ou dump SQL)
- ✅ **Espaço em disco** : ~20GB (para dados + processamento)
- ✅ **RAM** : Mínimo 4GB, recomendado 8GB

### Verificar instalações

```bash
# Verificar Python
python3 --version
# Esperado: Python 3.8+

# Verificar Docker
docker --version
docker-compose --version
# Esperado: Docker version 20+

# Verificar MySQL (se local)
mysql --version
# Esperado: mysql  Ver 8.0+ ou MariaDB 10.5+
```

### Dados phpBB necessários

Você deve ter acesso a :
- 📁 **Diretório do forum** : `/path/to/phpbb/` (clonado ou via FTP)
  - Contém `config.php`, `includes/`, `files/`, etc.
- 🗄️ **Base de dados MySQL** : Credenciais de acesso
  - OU um dump SQL completo (`phpbb_backup.sql`)

---

## 🔧 Preparação inicial

### Passo 1 : Clonar o repositório

```bash
git clone https://github.com/Gizmauwve/phpbb-discourse-migration.git
cd phpbb-discourse-migration
```

### Passo 2 : Verificar estrutura

```bash
ls -la
# Esperado:
# ├── scripts/
# ├── config/
# ├── docker-compose.yml
# ├── requirements.txt
# ├── README.md
# ├── CHECKLIST.md
# └── docs/
```

### Passo 3 : Criar ambiente Python

```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar (Linux/Mac)
source venv/bin/activate

# Ou no Windows
venv\Scripts\activate
```

### Passo 4 : Instalar dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Verificar instalação :
```bash
python -c "import pymysql; import requests; print('✓ Dependências OK')"
```

---

## 🔍 Detecção de versão

### ⚠️ PASSO CRÍTICO : Detectar versão phpBB

**Por que ?** Os scripts precisam saber qual versão phpBB você tem para adaptar as estruturas de dados.

### Opção 1 : Auto-detecção (Recomendado)

```bash
python scripts/detect_version.py --source ../Input --verbose
```

**O que faz :**
- ✅ Lê `includes/version.php`
- ✅ Conecta à base de dados e analisa estrutura
- ✅ Gera `config/version.json` com configuração detectada

**Saída esperada :**
```
✓ Found version 3.0.12 via version.php
✓ Database connection established
✓ phpBB version detected: 3.0.12
✓ Configuration saved to: config/version.json
```

### Opção 2 : Detecção manual

Se a auto-detecção falhar :

```bash
# 1. Verificar versão manualmente
cat ../Input/includes/version.php | grep version

# 2. Editar config/version.json
# Usar config/version.json.example como template
```

### Versões suportadas

| Versão | Suporte | Notas |
|--------|---------|-------|
| phpBB 2.0.x | ⚠️ Parcial | Estrutura muito diferente |
| **phpBB 3.0.x** | ✅ Completo | Totalmente suportado |
| phpBB 3.1.x | ✅ Completo | Compatível com 3.0.x |
| **phpBB 3.2.x** | ✅ Completo | Última versão estável |
| phpBB 3.3.x | ⚠️ Experimental | Pode ter problemas |
| phpBB 4.0.x | ❌ Não | Arquitetura diferente |

**Se versão não suportada :** Criar issue no GitHub.

---

## 📥 Instalação e configuração

### Passo 1 : Configurar Discourse local

```bash
# Iniciar containers Docker
docker-compose up -d

# Verificar status
docker-compose ps
# Esperado: discourse_postgres, discourse_redis, discourse_app = Up
```

### Passo 2 : Acessar setup wizard

1. Abrir navegador : http://localhost:3000
2. Completar setup :
   - Email admin
   - Username admin
   - Senha
   - Nome do site
3. Aguardar inicialização (pode levar 2-3 min)

### Passo 3 : Gerar API Key

1. Login como admin
2. Ir para : Admin → Settings → API
3. Clicar em "Generate New Key"
4. Copiar a key (será usado depois)

### Passo 4 : Verificar conexão

```bash
# Testar conexão com Discourse
python -c "import requests; r = requests.get('http://localhost:3000/api/categories'); print('✓ Discourse conectado' if r.status_code == 200 else '✗ Erro')"
```

---

## 🚀 Execução passo a passo

### PHASE 1️⃣ : EXPORT phpBB

Extrair dados da base phpBB para JSON.

```bash
python scripts/export_phpbb.py \
  --source ../Input \
  --output ./data/export \
  --verbose
```

**Parâmetros :**
- `--source` : Caminho do diretório phpBB (default: `../Input`)
- `--output` : Pasta de destino (default: `./data/export`)
- `--db-only` : Exportar apenas BD (sem arquivos)
- `--files-only` : Exportar apenas arquivos
- `--verbose` : Logs detalhados
- `--debug` : Stack traces completos

**O que acontece :**
```
✓ Conectando a MySQL...
✓ Exportando 1,234 usuários
✓ Exportando 45 categorias
✓ Exportando 5,678 tópicos
✓ Exportando 89,012 posts
✓ Copiando 8.69 GB de arquivos...
✓ Export concluído em 15 minutos
```

**Saídas geradas :**
```
data/export/
├── users.json           (1-2 MB)
├── categories.json      (50 KB)
├── topics.json          (5-10 MB)
├── posts.json           (100-500 MB)
├── attachments.json     (1-2 MB)
└── files/               (8+ GB)
    ├── avatars/
    ├── attachments/
    └── ...
```

**Logs :**
```bash
tail -f data/logs/export_phpbb.log
```

---

### PHASE 2️⃣ : CONVERT para Discourse

Converter dados phpBB para formato Discourse (NDJSON).

```bash
python scripts/convert_data.py \
  --input ./data/export \
  --output ./data/converted \
  --verbose
```

**Parâmetros :**
- `--input` : Pasta do export (default: `./data/export`)
- `--output` : Pasta de destino (default: `./data/converted`)
- `--skip-files` : Não copiar arquivos (dados apenas)
- `--mapping-file` : Arquivo de mapping customizado (JSON)
- `--verbose` : Logs detalhados

**O que acontece :**
```
✓ Convertendo usuários...
✓ Convertendo BBCode → Markdown...
✓ Mappeando categorias...
✓ Organizando tópicos e posts...
✓ Gerando cores das categorias...
✓ Conversão concluída em 5 minutos
```

**Conversões automáticas :**
```
[b]texto[/b]      → **texto**
[i]texto[/i]      → *texto*
[url=...]link[/url] → [link](...)
[img]url[/img]    → ![image](url)
[code]...[/code]  → ```...```
[quote="User"]... → > **User** wrote:\n> ...
```

**Saídas geradas :**
```
data/converted/
├── users.ndjson       (Formato Discourse)
├── categories.ndjson
├── topics.ndjson
├── posts.ndjson
└── files/             (Reorganizado)
```

**Logs :**
```bash
tail -f data/logs/convert_data.log
```

---

### PHASE 3️⃣ : IMPORT em Discourse

Importar dados no Discourse via API.

```bash
python scripts/import_discourse.py \
  --source ./data/converted \
  --target http://localhost:3000 \
  --api-key YOUR_API_KEY_HERE \
  --admin-email admin@example.com \
  --verbose
```

**Parâmetros :**
- `--source` : Pasta convertida (default: `./data/converted`)
- `--target` : URL Discourse (default: `http://localhost:3000`)
- `--api-key` : Chave API (OBRIGATÓRIO - copiar de Admin → API)
- `--admin-email` : Email do admin
- `--batch-size` : Itens por lote (default: 100)
- `--dry-run` : Simular sem importar
- `--verbose` : Logs detalhados

**IMPORTANTE : Gerar API Key**
```bash
# 1. Login no http://localhost:3000
# 2. Admin → Settings → API
# 3. Clicar em "Generate New Key"
# 4. Copiar a chave:
echo "sk-xxxxxxxxxxxxxxxxxxxx"
```

**Teste primeiro (dry-run) :**
```bash
python scripts/import_discourse.py \
  --source ./data/converted \
  --target http://localhost:3000 \
  --api-key YOUR_API_KEY \
  --dry-run --verbose
```

**Depois import real :**
```bash
python scripts/import_discourse.py \
  --source ./data/converted \
  --target http://localhost:3000 \
  --api-key YOUR_API_KEY \
  --verbose
```

**O que acontece :**
```
=== Importing Users ===
Users |████████████████| 1,234 [00:45<00:00]
✓ Imported 1,234/1,234 users

=== Importing Categories ===
Categories |████████████| 45 [00:02<00:00]
✓ Imported 45/45 categories

=== Importing Topics ===
Topics |████████████████| 5,678 [05:30<00:00]
✓ Imported 5,678/5,678 topics

=== Importing Posts ===
Posts |████████████████| 89,012 [45:20<00:00]
✓ Imported 89,012/89,012 posts

✓ Import completed successfully!
```

**Logs :**
```bash
tail -f data/logs/import_discourse.log
```

---

### PHASE 4️⃣ : VALIDATE Migração

Validar que todos os dados foram importados corretamente.

```bash
python scripts/validate_migration.py \
  --phpbb ../Input \
  --discourse http://localhost:3000 \
  --verbose
```

**Parâmetros :**
- `--phpbb` : Caminho phpBB (default: `../Input`)
- `--discourse` : URL Discourse (default: `http://localhost:3000`)
- `--output` : Arquivo de relatório (default: `data/logs/validation.html`)
- `--verbose` : Logs detalhados

**O que valida :**
```
=== Validating Users ===
phpBB users: 1,234
Discourse users: 1,234
✓ User count matches

=== Validating Categories ===
phpBB categories: 45
Discourse categories: 45
✓ Category count matches

=== Validating Topics ===
phpBB topics: 5,678
Discourse topics: 5,678
✓ Topic count matches

=== Validating Posts ===
phpBB posts: 89,012
Discourse posts: 89,012
✓ Post count matches

✓ All validations passed!
```

**Abrir relatório HTML :**
```bash
open data/logs/validation.html
# Ou usar seu navegador: file:///absolute/path/data/logs/validation.html
```

---

## ✅ Validação e testes

### Checklist de validação

Use **`CHECKLIST.md`** para validação completa :

```bash
# Ver checklist
cat CHECKLIST.md

# Ou abrir em editor
vscode CHECKLIST.md
```

### Testes manuais no Discourse

1. **Login e navegação**
   - [ ] Acessar http://localhost:3000
   - [ ] Login como admin
   - [ ] Ver todas as categorias
   - [ ] Clicar em tópicos
   - [ ] Ver posts

2. **Conteúdo**
   - [ ] Textos aparecem corretamente
   - [ ] Imagens carregam
   - [ ] BBCode foi convertido para Markdown
   - [ ] Avatares aparecem

3. **Metadados**
   - [ ] Datas de criação corretas
   - [ ] Nomes de usuários corretos
   - [ ] Contagem de posts por tópico

### Comparação phpBB vs Discourse

```bash
# Ver estatísticas de export
jq 'length' data/export/users.json
jq 'length' data/export/posts.json

# Comparar com Discourse via API
curl -s http://localhost:3000/api/users | jq '.users | length'
curl -s http://localhost:3000/api/posts | jq '.posts | length'
```

---

## 🔧 Troubleshooting

### Erro : "config.php not found"

```
FileNotFoundError: config.php not found at /path/to/Input/config.php
```

**Solução :**
```bash
# Verificar caminho
ls -la ../Input/config.php

# Se não existe, copiar corretamente
cp /path/correto/phpbb/config.php ../Input/

# Tentar novamente
python scripts/export_phpbb.py --source ../Input --verbose
```

### Erro : "Database connection refused"

```
ConnectionRefusedError: (2003, "Can't connect to MySQL server")
```

**Solução :**
```bash
# Verificar MySQL
mysql -h localhost -u phpbb_user -p -e "SELECT 1"

# Se erro, verificar credenciais em config.php
grep -E "dbhost|dbuser|dbpasswd|dbname" ../Input/config.php

# Editar config/version.json com credenciais corretas
```

### Erro : "401 Unauthorized" (API Key inválida)

```
401 Unauthorized: Invalid API key
```

**Solução :**
```bash
# Verificar se Discourse está rodando
docker-compose ps

# Regenerar API key
# 1. Acessar http://localhost:3000
# 2. Admin → Settings → API
# 3. Click "Generate New Key"
# 4. Copiar nova chave

# Tentar import novamente
python scripts/import_discourse.py ... --api-key NEW_KEY_HERE
```

### Erro : "Timeout" durante import

```
TimeoutError: Request timed out
```

**Solução :**
```bash
# Reduzir batch size
python scripts/import_discourse.py \
  ... \
  --batch-size 50 \
  --verbose

# Ou aumentar memória de Discourse
docker-compose down
# Editar docker-compose.yml: aumentar memory_limit
docker-compose up -d
```

### Erro : "Espaço em disco insuficiente"

```
DiskError: No space left on device
```

**Solução :**
```bash
# Verificar espaço
df -h

# Limpar dados antigos
rm -rf data/export data/converted data/logs/*

# Ou usar --skip-files para migrar dados apenas
python scripts/convert_data.py --input ./data/export --skip-files
```

### Ver logs completos

```bash
# Export logs
tail -100 data/logs/export_phpbb.log

# Convert logs
tail -100 data/logs/convert_data.log

# Import logs
tail -100 data/logs/import_discourse.log

# Validation logs
tail -100 data/logs/validation.log

# Todos os logs (live)
watch 'ls -lt data/logs/*.log | head -1 && tail -10 data/logs/*.log'
```

---

## 📊 Exemplo de execução completa

### Cenário : Migração 8.69 GB com phpBB 3.0.12

```bash
# ======================================
# 1. SETUP
# ======================================
cd phpbb-discourse-migration
source venv/bin/activate

# ======================================
# 2. DETECT VERSION
# ======================================
python scripts/detect_version.py --source ../Input --verbose
# ✓ Found version 3.0.12

# ======================================
# 3. START DISCOURSE
# ======================================
docker-compose up -d
sleep 60  # Aguardar inicialização
open http://localhost:3000  # Setup wizard
# Completar setup... copiar API key

# ======================================
# 4. EXPORT
# ======================================
time python scripts/export_phpbb.py --source ../Input --verbose
# ✓ Export concluído em 15 minutos

# ======================================
# 5. CONVERT
# ======================================
time python scripts/convert_data.py --input ./data/export --verbose
# ✓ Conversion concluído em 5 minutos

# ======================================
# 6. DRY RUN
# ======================================
python scripts/import_discourse.py \
  --source ./data/converted \
  --target http://localhost:3000 \
  --api-key sk-xxxx \
  --dry-run --verbose
# ✓ Simulation OK

# ======================================
# 7. IMPORT REAL
# ======================================
time python scripts/import_discourse.py \
  --source ./data/converted \
  --target http://localhost:3000 \
  --api-key sk-xxxx \
  --verbose
# ✓ Import concluído em 60 minutos

# ======================================
# 8. VALIDATE
# ======================================
time python scripts/validate_migration.py \
  --phpbb ../Input \
  --discourse http://localhost:3000 \
  --verbose
# ✓ Validation OK
open data/logs/validation.html

# ======================================
# ✅ MIGRATION COMPLETE
# ======================================
echo "Forum migrado com sucesso!"
echo "Acessar: http://localhost:3000"
```

**Tempo total esperado :** ~90 minutos para 8.69 GB
- Export : 15 min
- Convert : 5 min
- Import : 60 min
- Validate : 5 min
- Setup/overhead : 5 min

---

## 🎯 Próximos passos

### Após validação bem-sucedida

1. **Testes com usuários**
   - Criar algumas contas teste
   - Testar login/navegação
   - Verificar permissões

2. **Otimização**
   - Rebuild search index : `./rake search:index`
   - Vacuum database : `./rake db:vacuum`
   - Precompile assets : `./rake assets:precompile`

3. **Backup Discourse**
   ```bash
   docker exec discourse_app ./bin/discourse backup
   ```

4. **Produção** (se aplicável)
   - Deploy em servidor prod
   - Configurar domínio
   - SSL/HTTPS
   - Backups regulares

5. **Documentação**
   - Arquivar logs
   - Documentar customizações
   - Criar runbook para futuros admins

### Recursos adicionais

- **Discourse docs** : https://meta.discourse.org
- **GitHub issues** : https://github.com/Gizmauwve/phpbb-discourse-migration/issues
- **Chat support** : Discord/Slack (se aplicável)

---

## 📞 Suporte

**Algo deu errado ?**

1. Verificar **CHECKLIST.md** para troubleshooting
2. Revisar logs em `data/logs/`
3. Testar com `--verbose` e `--debug`
4. Criar issue no GitHub com :
   - Versão phpBB
   - Comando executado
   - Erro completo
   - Logs relevantes

---

**Sucesso na migração! 🚀**
