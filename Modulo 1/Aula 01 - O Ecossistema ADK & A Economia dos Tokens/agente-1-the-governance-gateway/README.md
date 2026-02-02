# Aula 01: O Ecossistema ADK & A Economia dos Tokens

# Governance Gateway

Sistema de Roteamento Inteligente de Modelos LLM baseado no padrão **Router-Gateway** para otimização de custos (FinOps).

## 📋 Sobre o Projeto

O **Governance Gateway** é um sistema de demonstração que implementa o padrão Router-Gateway para escolha dinâmica de modelos LLM (Gemini Pro vs Flash) baseado em:

- **Tier do departamento** (platinum, standard, budget)
- **Complexidade da requisição** (score 0.0 a 1.0)
- **Política configurável via YAML**

### Objetivo

Demonstrar como desacoplar a escolha do modelo do código de negócio, permitindo otimização de custos (FinOps) sem alterar código de produção.

## 🏗️ Arquitetura

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │
       ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Router    │────▶│   Gateway    │────▶│ Vertex AI   │
│  (YAML)     │     │  (Abstraction)│     │  (Models)   │
└─────────────┘     └──────────────┘     └─────────────┘
       │
       ▼
┌─────────────┐
│ Telemetry   │
│  (FinOps)   │
└─────────────┘
```

### Componentes Principais

- **Router** (`src/router.py`): Decide qual modelo usar baseado em política YAML
- **Telemetry** (`src/telemetry.py`): Calcula custos em tempo real
- **Models** (`src/models.py`): Validação de dados com Pydantic
- **Main** (`src/main.py`): Script de demonstração

## 🚀 Instalação

### Pré-requisitos

- Python 3.8+
- pip

### Passos

1. **Clone o repositório** (ou navegue até o diretório do projeto)

2. **Instale as dependências**:

```bash
pip install -r requirements.txt
```

3. **Verifique a estrutura**:

```
governance-gateway/
├── config/
│   ├── model_policy.yaml      # Política de roteamento
│   └── safety_settings.yaml   # Configurações de segurança
├── prompts/
│   ├── audit_master.jinja2    # Template do prompt
│   └── user_intent.yaml       # Few-shot examples
├── src/
│   ├── router.py              # Lógica de roteamento
│   ├── telemetry.py           # Cálculo de custos
│   ├── models.py              # Validação Pydantic
│   ├── exceptions.py          # Exceções customizadas
│   ├── logger.py             # Sistema de logging
│   └── main.py               # Script de demonstração
└── tests/                     # Testes unitários
```

## 💻 Uso

### Executar Demonstração

```bash
python main.py
```

Ou alternativamente:

```bash
python -m src.main
```

**Nota para usuários Windows:** Se encontrar erro de encoding (UnicodeEncodeError), execute com:

```bash
chcp 65001 && python main.py
```

Ou defina a variável de ambiente:

```bash
$env:PYTHONIOENCODING="utf-8"
python main.py
```

A demonstração simula 3 requisições de diferentes departamentos:

1. **Departamento Jurídico** (Tier Platinum) → Sempre usa Gemini Pro
2. **Recursos Humanos** (Tier Standard) → Flash ou Pro baseado em complexidade
3. **Operações de TI** (Tier Budget) → Sempre usa Gemini Flash

### Exemplo de Saída

```
━━━ Cenário 1: Departamento Jurídico ━━━

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Atributo          │ Valor                                                         ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Departamento      │ Departamento Jurídico                                         │
│ Complexidade      │ 0.80                                                          │
│ Modelo Escolhido  │ gemini-1.5-pro-001                                           │
│ Custo Estimado    │ $0.000123 USD                                                │
└───────────────────┴───────────────────────────────────────────────────────────────┘
```

## ⚙️ Configuração

### Política de Roteamento (`config/model_policy.yaml`)

Define as regras de negócio para escolha do modelo:

```yaml
departments:
  legal_dept:
    tier: platinum # Sempre usa Pro
    model: gemini-1.5-pro-001
    complexity_threshold: null

  hr_dept:
    tier: standard # Decisão dinâmica
    model: null
    complexity_threshold: 0.5 # < 0.5 = Flash, >= 0.5 = Pro

  it_ops:
    tier: budget # Sempre usa Flash
    model: gemini-1.5-flash-001
    complexity_threshold: null

pricing:
  gemini-1.5-pro-001:
    input_per_1k_tokens: 0.00125
    output_per_1k_tokens: 0.00500

  gemini-1.5-flash-001:
    input_per_1k_tokens: 0.000075
    output_per_1k_tokens: 0.00030
```

### Tiers Disponíveis

- **platinum**: Sempre usa Gemini Pro (máxima qualidade, maior custo)
- **standard**: Decisão dinâmica baseada em `complexity_score`
- **budget**: Sempre usa Gemini Flash (menor custo, boa qualidade)

## 🧪 Testes

### Executar Todos os Testes

```bash
pytest tests/ -v
```

### Executar Testes Específicos

```bash
# Testes do Router
pytest tests/test_router.py -v

# Testes de Telemetria
pytest tests/test_telemetry.py -v

# Testes de Modelos
pytest tests/test_models.py -v
```

### Cobertura de Testes

```bash
pytest tests/ --cov=src --cov-report=html
```

**Status**: 44 testes, 100% passando ✅

## 📊 Estrutura de Dados

### Resposta do Auditor

```json
{
  "compliance_status": "APPROVED" | "REJECTED" | "REQUIRES_REVIEW",
  "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
  "audit_reasoning": "Texto explicativo detalhado"
}
```

## 🔍 Logging

O sistema utiliza logging estruturado. Para configurar o nível:

```python
from src.logger import setup_logging

# Configurar logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
setup_logging(level="INFO")
```

Logs incluem:

- Carregamento de políticas
- Decisões de roteamento
- Cálculos de custos
- Erros e exceções

## 🛠️ Desenvolvimento

### Estrutura do Código

```
src/
├── router.py          # Lógica de roteamento
├── telemetry.py       # Cálculo de custos (FinOps)
├── models.py          # Modelos Pydantic para validação
├── exceptions.py      # Exceções customizadas
├── logger.py          # Configuração de logging
└── main.py            # Script de demonstração
```

### Adicionar Novo Departamento

1. Edite `config/model_policy.yaml`:

```yaml
departments:
  novo_dept:
    tier: standard
    model: null
    complexity_threshold: 0.6
```

2. O sistema automaticamente valida e carrega a nova configuração.

### Adicionar Novo Modelo

1. Edite `config/model_policy.yaml`:

```yaml
pricing:
  novo-modelo:
    input_per_1k_tokens: 0.001
    output_per_1k_tokens: 0.004
```

2. Atualize `src/models.py` para incluir o novo modelo na lista de válidos.

## 🚨 Tratamento de Erros

O sistema utiliza exceções customizadas para melhor rastreamento:

- `PolicyValidationError`: Erro ao validar política YAML
- `PolicyNotFoundError`: Arquivo de política não encontrado
- `TemplateNotFoundError`: Template Jinja2 não encontrado
- `ModelNotFoundError`: Modelo não encontrado na política
- `DepartmentNotFoundError`: Departamento não encontrado
- `InvalidComplexityError`: Score de complexidade inválido

## 📈 FinOps

O sistema calcula custos em tempo real baseado em:

- **Tokens de input**: Prompt enviado ao modelo
- **Tokens de output**: Resposta do modelo
- **Preços por modelo**: Configurados em `model_policy.yaml`

**Fórmula**:

```
Custo = (input_tokens / 1000) * preço_input + (output_tokens / 1000) * preço_output
```

## 🔐 Segurança

- Validação de inputs com Pydantic
- Sanitização de dados
- Safety settings configuráveis (ver `config/safety_settings.yaml`)

## 📝 Notas Importantes

### Demonstração vs Produção

⚠️ **Este é um projeto de demonstração**. Para uso em produção:

1. **Integração Real com Vertex AI**: Substitua `simulate_llm_response()` por chamadas reais
2. **Autenticação**: Configure credenciais do Google Cloud
3. **Rate Limiting**: Implemente controle de taxa
4. **Cache**: Adicione cache para políticas e templates
5. **Métricas**: Implemente sistema de métricas completo

### Aproximação de Tokens

O sistema usa aproximação **1 token ≈ 4 caracteres**. Em produção, use:

- `tiktoken` para contagem precisa
- API do Vertex AI que retorna tokens reais

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto é para fins educacionais e demonstração.

## 👥 Autores

- Desenvolvido para curso avançado de Engenharia de Agentes
- Padrão Router-Gateway para FinOps

## 🎓 Notas Pedagógicas - Conexão com o Curso

### Aula 01: O Ecossistema ADK & A Economia dos Tokens

Este projeto estabelece os fundamentos que serão expandidos nas próximas aulas:

#### ✅ Conceitos Demonstrados Nesta Aula

**1. Estrutura ADK (Agent Development Kit)**

- Por que separar `prompts/`, `tools/` e `config/`?
- Versionamento de configurações e templates
- Desacoplamento de código e configuração
- Auditoria de mudanças via Git

**2. FinOps (Financial Operations)**

- Monitoramento de custos em tempo real
- Comparativo prático: Gemini Flash vs Pro
- Cálculo preciso de tokens (tiktoken)
- Impacto financeiro de escolhas de modelo

**3. Router-Gateway Pattern**

- Desacoplamento da escolha do modelo
- Políticas configuráveis via YAML
- Otimização de custos sem alterar código

#### 🔮 Próximas Aulas - O que vem depois

**Aula 02: Engenharia de Prompt & Intenção Segura**

- Implementaremos "Intent Guardrail" neste mesmo projeto
- O agente analisará se a pergunta é segura antes de responder
- Bloqueio de prompt injection e engenharia social
- Chain-of-Thought para maior precisão em tarefas bancárias
- Configuração de personas via YAML do ADK

**Aula 03: Output Estruturado (JSON) & Integração Legada**

- Substituiremos `simulate_llm_response()` por chamadas reais ao Vertex AI
- Uso de `response_mime_type="application/json"` para garantir JSON válido
- Validação robusta com Pydantic (retry se JSON inválido)
- Integração simulada com API REST interna
- Tokens reais da API (não mais estimativa)

#### 🎯 Por que Simulação Agora?

Na Aula 01, focamos em:

- ✅ Arquitetura e padrões (Router-Gateway)
- ✅ FinOps e economia de tokens
- ✅ Estrutura ADK padronizada

Evitamos na Aula 01:

- ❌ Complexidade de autenticação ADC
- ❌ Integração real com APIs (vem na Aula 03)
- ❌ Tratamento avançado de erros (vem nas aulas futuras)

**Foco pedagógico**: Estabelecer fundamentos antes de adicionar complexidade.

#### 📊 Comparativo de Custos - Demonstração Prática

Exemplo real demonstrado neste projeto:

| Modelo           | Input (1M tokens) | Output (1M tokens) | Multiplicador  |
| ---------------- | ----------------- | ------------------ | -------------- |
| **Gemini Flash** | $0.075            | $0.30              | 1x (baseline)  |
| **Gemini Pro**   | $1.25             | $5.00              | ~16x mais caro |

**Simulação de uso real**:

- Requisição típica: 1000 tokens input, 500 tokens output
- **Flash**: (1000/1000)×$0.075 + (500/1000)×$0.30 = **$0.225**
- **Pro**: (1000/1000)×$1.25 + (500/1000)×$5.00 = **$3.75**
- **Diferença**: Pro é 16.7x mais caro!

**Impacto anual** (1000 requisições/dia):

- Sempre Pro: ~$3.75/dia = ~$1,368/ano
- Roteamento inteligente (70% Flash, 30% Pro): ~$0.80/dia = ~$292/ano
- **Economia**: ~$1,076/ano por agente (79% de redução!)

---

### 🛠️ Setup do Ambiente - Aula 01

**Pré-requisitos:**

- Python 3.8+
- VS Code com extensão "Google Cloud Code" (recomendado)
- Git para versionamento

**Instalação:**

```bash
# 1. Clonar ou navegar até o diretório do projeto
cd governance-gateway

# 2. Criar ambiente virtual (recomendado)
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# 3. Instalar dependências
pip install -r requirements.txt

# 4. Executar demonstração
python main.py

# 5. Executar testes
pytest tests/ -v
```

**Nota sobre autenticação**:

- **Aula 01**: Não é necessária (usamos simulação)
- **Aula 03**: Será necessária a configuração ADC:
  ```bash
  gcloud auth application-default login
  ```

---

## 🔗 Referências

- [Google Cloud Vertex AI](https://cloud.google.com/vertex-ai)
- [Pydantic](https://docs.pydantic.dev/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [Pytest](https://docs.pytest.org/)
- [Tiktoken](https://github.com/openai/tiktoken)

---

**Versão**: 1.0.0  
**Última atualização**: 2024
