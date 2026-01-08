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
python src/main.py
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

## 🔗 Referências

- [Google Cloud Vertex AI](https://cloud.google.com/vertex-ai)
- [Pydantic](https://docs.pydantic.dev/)
- [Jinja2](https://jinja.palletsprojects.com/)
- [Pytest](https://docs.pytest.org/)

---

**Versão**: 1.0.0  
**Última atualização**: 2024
