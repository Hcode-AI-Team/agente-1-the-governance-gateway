# Aula 01: O Ecossistema ADK & A Economia dos Tokens

# Governance Gateway

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Tests](https://img.shields.io/badge/tests-44%20passing-brightgreen.svg)
![License](https://img.shields.io/badge/license-Educational-orange.svg)
![Status](https://img.shields.io/badge/status-Active-success.svg)

Sistema de Roteamento Inteligente de Modelos LLM baseado no padrão **Router-Gateway** para otimização de custos (FinOps).

## 📑 Índice

- [Sobre o Projeto](#-sobre-o-projeto)
- [Quick Start](#-quick-start)
- [Arquitetura](#️-arquitetura)
- [Instalação](#-instalação-detalhada)
- [Uso](#-uso)
- [Configuração](#️-configuração)
- [Testes](#-testes)
- [FinOps](#-finops---otimização-de-custos)
- [Desenvolvimento](#️-desenvolvimento)
- [Segurança](#-segurança-e-validação)
- [Notas Pedagógicas](#-notas-pedagógicas---conexão-com-o-curso)
- [FAQ](#-faq---perguntas-frequentes)
- [Referências](#-referências-e-recursos)

---

## 📋 Sobre o Projeto

O **Governance Gateway** é um sistema educacional de demonstração que implementa o padrão **Router-Gateway** para seleção inteligente de modelos LLM (Gemini Pro vs Flash), otimizando custos através de políticas configuráveis.

### O que o projeto faz atualmente

Este projeto é uma **demonstração completa e funcional** que simula um sistema de auditoria bancária inteligente. Ele:

1. **Roteia requisições** para diferentes modelos LLM baseado em regras de negócio
2. **Calcula custos em tempo real** usando tokenização precisa (tiktoken)
3. **Simula respostas de auditoria** com diferentes níveis de compliance
4. **Valida dados** com Pydantic garantindo type safety
5. **Registra logs estruturados** de todas as operações
6. **Demonstra FinOps** comparando custos entre Gemini Flash e Pro

### Decisão de Roteamento

O sistema decide qual modelo usar baseado em:

- **Tier do departamento** (platinum, standard, budget)
- **Complexidade da requisição** (score 0.0 a 1.0)
- **Política configurável via YAML** (sem alteração de código)

### Objetivo Pedagógico

Demonstrar como desacoplar a escolha do modelo do código de negócio, permitindo:
- ✅ **Otimização de custos** (FinOps) sem alterar código de produção
- ✅ **Políticas auditáveis** via versionamento Git
- ✅ **Estrutura ADK** padronizada para agentes de IA
- ✅ **Cálculo preciso de custos** para tomada de decisão

## 🏗️ Arquitetura

### Fluxo de Execução Atual

```
┌─────────────┐
│   main.py   │  ← Ponto de entrada simples
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ src.main    │  ← Orquestra a demonstração
└──────┬──────┘
       │
       ├──▶ ModelRouter ────▶ model_policy.yaml (Decisão de modelo)
       │                            │
       │                            ▼
       ├──▶ render_prompt ────▶ audit_master.jinja2 (Template)
       │
       ├──▶ simulate_llm ────▶ Mock Response (Aula 01: simulação)
       │                            │
       │                            ▼
       └──▶ CostEstimator ───▶ Cálculo FinOps (tiktoken)
                                     │
                                     ▼
                              Exibição com Rich
```

### Componentes Principais

| Componente | Arquivo | Responsabilidade |
|------------|---------|------------------|
| **Ponto de Entrada** | `main.py` | Execução simplificada (`python main.py`) |
| **Router** | `src/router.py` | Decide qual modelo usar baseado em tier/complexidade |
| **Telemetry** | `src/telemetry.py` | Calcula custos em tempo real com tiktoken |
| **Models** | `src/models.py` | Validação de dados com Pydantic |
| **Orchestrator** | `src/main.py` | Script de demonstração e orquestração |
| **Logger** | `src/logger.py` | Sistema de logging estruturado |
| **Exceptions** | `src/exceptions.py` | Exceções customizadas para rastreamento |

### Estado Atual vs Futuro

**Aula 01 (Implementado):**
- ✅ Router com políticas YAML
- ✅ Cálculo de custos (FinOps)
- ✅ Simulação de LLM (mock)
- ✅ Validação Pydantic
- ✅ Templates Jinja2
- ✅ Logging estruturado

**Próximas Aulas:**
- 🔜 **Aula 02**: Intent Guardrail (validação de intenção)
- 🔜 **Aula 03**: Integração real com Vertex AI
- 🔜 **Aula 03**: Output estruturado JSON garantido

## ⚡ Quick Start

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Executar demonstração
python main.py

# 3. Executar testes
pytest tests/ -v
```

**Pronto!** O sistema vai demonstrar 3 cenários de roteamento diferentes.

---

## 🚀 Instalação Detalhada

### Pré-requisitos

- Python 3.8+
- pip (gerenciador de pacotes Python)
- Ambiente virtual (recomendado)

### Passos Completos

1. **Clone o repositório** (ou navegue até o diretório do projeto)

2. **(Recomendado) Crie um ambiente virtual**:

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

3. **Instale as dependências**:

```bash
pip install -r requirements.txt
```

3. **Verifique a estrutura do projeto**:

```
governance-gateway/
├── main.py                    # ← Ponto de entrada (python main.py)
├── .gitignore                 # ← Ignora cache e venv
├── requirements.txt           # Dependências Python
├── pytest.ini                 # Configuração do pytest
├── README.md                  # Esta documentação
│
├── config/                    # 📁 Configurações (YAML)
│   ├── model_policy.yaml      # Política de roteamento e preços
│   └── safety_settings.yaml   # Safety settings do Vertex AI
│
├── prompts/                   # 📁 Templates e exemplos (ADK)
│   ├── audit_master.jinja2    # Template do prompt do sistema
│   └── user_intent.yaml       # Few-shot examples (classificação)
│
├── src/                       # 📁 Código Python
│   ├── __init__.py            # Inicialização do pacote
│   ├── main.py                # Orquestrador da demonstração
│   ├── router.py              # Lógica de roteamento por tier
│   ├── telemetry.py           # Cálculo de custos (FinOps + tiktoken)
│   ├── models.py              # Validação Pydantic
│   ├── exceptions.py          # Exceções customizadas
│   └── logger.py              # Sistema de logging estruturado
│
└── tests/                     # 📁 Testes unitários (44 testes)
    ├── __init__.py
    ├── test_main.py           # Testes do orquestrador
    ├── test_router.py         # Testes de roteamento
    ├── test_telemetry.py      # Testes de cálculo de custos
    └── test_models.py         # Testes de validação Pydantic
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
├── main.py                 # Ponto de entrada principal
│
src/
├── __init__.py             # Define o pacote e versão
├── main.py                 # Orquestração da demonstração
├── router.py               # Lógica de roteamento (tier → modelo)
├── telemetry.py            # Cálculo de custos (FinOps + tiktoken)
├── models.py               # Modelos Pydantic para validação
├── exceptions.py           # Exceções customizadas
└── logger.py               # Configuração de logging estruturado
```

### Tecnologias Utilizadas

| Tecnologia | Propósito | Versão |
|------------|-----------|--------|
| **Python** | Linguagem principal | 3.8+ |
| **Pydantic** | Validação de dados | 2.5.0+ |
| **PyYAML** | Parsing de configurações | 6.0.1+ |
| **Jinja2** | Templates de prompts | 3.1.2+ |
| **Rich** | Interface CLI formatada | 13.7.0+ |
| **tiktoken** | Contagem precisa de tokens | 0.5.0+ |
| **pytest** | Testes unitários | 7.4.0+ |
| **google-cloud-aiplatform** | SDK Vertex AI (futuro) | 1.38.0+ |

### Como Estender o Projeto

#### Adicionar Novo Departamento

1. Edite `config/model_policy.yaml`:

```yaml
departments:
  marketing_dept:
    tier: standard
    model: null
    complexity_threshold: 0.6
```

2. Execute o programa - o sistema valida automaticamente com Pydantic
3. Se houver erro de validação, o programa falha na inicialização (fail-fast)

#### Adicionar Novo Modelo LLM

1. Adicione os preços em `config/model_policy.yaml`:

```yaml
pricing:
  gemini-2.0-ultra:
    input_per_1k_tokens: 0.002
    output_per_1k_tokens: 0.008
```

2. Atualize a lista de modelos válidos em `src/models.py`:

```python
valid_models = [
    'gemini-1.5-pro-001',
    'gemini-1.5-flash-001',
    'gemini-2.0-ultra'  # ← Adicione aqui
]
```

3. Execute os testes para verificar a integração:

```bash
pytest tests/test_models.py -v
```

#### Personalizar Prompt de Auditoria

1. Edite `prompts/audit_master.jinja2`
2. Modifique as instruções do sistema
3. Adicione variáveis Jinja2 se necessário: `{{ nova_variavel }}`
4. Teste com diferentes entradas

## 🚨 Tratamento de Erros

O sistema utiliza exceções customizadas para melhor rastreamento:

- `PolicyValidationError`: Erro ao validar política YAML
- `PolicyNotFoundError`: Arquivo de política não encontrado
- `TemplateNotFoundError`: Template Jinja2 não encontrado
- `ModelNotFoundError`: Modelo não encontrado na política
- `DepartmentNotFoundError`: Departamento não encontrado
- `InvalidComplexityError`: Score de complexidade inválido

## 📈 FinOps - Otimização de Custos

### Como funciona o cálculo de custos

O sistema calcula custos em tempo real baseado em:

1. **Tokens de input**: Prompt enviado ao modelo (contado com tiktoken)
2. **Tokens de output**: Resposta do modelo (contado com tiktoken)
3. **Preços por modelo**: Configurados em `model_policy.yaml`

**Fórmula de custo**:

```python
custo_input  = (input_tokens / 1000) * preço_input_por_1k
custo_output = (output_tokens / 1000) * preço_output_por_1k
custo_total  = custo_input + custo_output
```

### Pipeline de FinOps

```
1. Texto → tiktoken → Contagem de tokens
2. Tokens × Preços → Custo estimado
3. Decisão: Flash ou Pro? → Otimização
4. Log estruturado → Auditoria
```

### Por que isso importa?

- 🔴 **Sem otimização**: Usar sempre Pro = $1,368/ano por agente
- 🟢 **Com roteamento inteligente**: 70% Flash, 30% Pro = $292/ano
- 💰 **Economia**: **$1,076/ano** (79% de redução) por agente

Em uma empresa com 50 agentes: **$53,800/ano de economia**!

## 🔐 Segurança e Validação

### Camadas de Segurança Implementadas

1. **Validação de Tipos (Pydantic)**
   - Todos os dados de entrada são validados
   - Type safety garantido em tempo de execução
   - Erros detectados antes do processamento

2. **Validação de Políticas (YAML)**
   - Políticas validadas na inicialização (fail-fast)
   - Prevenção de configurações inválidas
   - Mensagens de erro claras

3. **Exceções Customizadas**
   - Rastreamento granular de erros
   - Logs estruturados para auditoria
   - Stack traces informativos

4. **Safety Settings (Vertex AI)**
   - Configuradas em `config/safety_settings.yaml`
   - Serão aplicadas na integração real (Aula 03)
   - Bloqueio de conteúdo prejudicial

### Validações Implementadas

| Validação | Componente | Erro Lançado |
|-----------|------------|--------------|
| Tier inválido | `models.py` | `ValidationError` |
| Modelo desconhecido | `models.py` | `ValidationError` |
| Complexity fora de range | `router.py` | `InvalidComplexityError` |
| Departamento inexistente | `router.py` | `DepartmentNotFoundError` |
| YAML malformado | `router.py` | `PolicyValidationError` |
| Template não encontrado | `main.py` | `TemplateNotFoundError` |

## 📝 Notas Importantes

### Status do Projeto: Demonstração Educacional

⚠️ **Este é um projeto de demonstração para ensino**. Veja o que está implementado vs o que seria necessário em produção:

| Funcionalidade | Aula 01 (Atual) | Produção |
|----------------|-----------------|----------|
| **Roteamento de modelos** | ✅ Implementado | ✅ Pronto para produção |
| **Cálculo de custos** | ✅ Implementado (tiktoken) | ✅ Pronto (API retorna tokens) |
| **Validação Pydantic** | ✅ Implementado | ✅ Pronto para produção |
| **Logging estruturado** | ✅ Implementado | ✅ Pronto para produção |
| **Chamadas LLM** | ⚠️ Simulação (mock) | ❌ Requer integração Vertex AI |
| **Autenticação ADC** | ⚠️ Não necessária | ❌ Requer `gcloud auth` |
| **Rate limiting** | ❌ Não implementado | ❌ Requer implementação |
| **Cache de políticas** | ❌ Carrega toda vez | ❌ Requer cache (Redis?) |
| **Monitoramento** | ⚠️ Logs básicos | ❌ Requer APM (Datadog, etc.) |

### Próximos Passos para Produção

**Aula 02 (Intent Guardrail):**
- Validação de intenção do usuário
- Bloqueio de prompt injection
- Chain-of-Thought para precisão

**Aula 03 (Integração Real):**
- Substituir `simulate_llm_response()` por:
  ```python
  from vertexai.generative_models import GenerativeModel
  model = GenerativeModel("gemini-1.5-pro-001")
  response = model.generate_content(prompt)
  ```
- Configurar autenticação ADC
- Usar tokens reais da API
- Output estruturado JSON garantido

**Melhorias de Produção (não cobertas no curso):**
- Rate limiting e retry logic
- Cache distribuído (Redis)
- Monitoramento e alertas
- CI/CD pipeline
- Testes de integração
- Documentação OpenAPI

### Contagem de Tokens

O sistema usa **`tiktoken`** (biblioteca da OpenAI) para contagem precisa de tokens:

- ✅ **Método atual**: `tiktoken` com encoding `cl100k_base`
- ✅ **Precisão**: ~95% de precisão para modelos Gemini
- ⚠️ **Fallback**: Se tiktoken não disponível, usa aproximação (1 token ≈ 4 chars)

**Em produção com Vertex AI:**
```python
# A API retorna contagem exata
response.usage_metadata.prompt_token_count      # Input tokens
response.usage_metadata.candidates_token_count  # Output tokens
```

**Por que tiktoken funciona para Gemini?**
- Gemini usa tokenização similar aos modelos GPT
- O encoding `cl100k_base` é uma boa aproximação
- Para cálculos de custo, a precisão é suficiente

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

## ❓ FAQ - Perguntas Frequentes

### Por que usar simulação em vez de integração real?

**Objetivo pedagógico**: Na Aula 01, focamos em fundamentos (arquitetura, FinOps, ADK). A integração real adiciona complexidade (autenticação, errors handling, custos reais) que distrairia do aprendizado dos conceitos centrais.

### O tiktoken funciona para Gemini?

**Sim**, com boa precisão (~95%). Gemini usa tokenização similar ao GPT-4. Para produção, a API do Vertex AI retorna tokens exatos, mas tiktoken é suficiente para demonstração e estimativas.

### Posso usar este código em produção?

**Parcialmente**. O Router, Telemetry, Models e Logger estão prontos. Você precisaria:
1. Substituir `simulate_llm_response()` por chamadas reais
2. Configurar autenticação do Google Cloud
3. Adicionar tratamento de erros de rede
4. Implementar retry logic e rate limiting

### Por que YAML para políticas?

YAML permite:
- ✅ Versionamento no Git (auditável)
- ✅ Mudanças sem alterar código
- ✅ Fácil revisão em pull requests
- ✅ Separação de responsabilidades (devs vs FinOps)

### Como adicionar suporte a outros modelos LLM?

1. Adicione preços em `config/model_policy.yaml`
2. Atualize lista de modelos em `src/models.py`
3. Ajuste a tokenização se necessário (tiktoken suporta vários encodings)

---

## 🔗 Referências e Recursos

### Documentação Oficial

- [Google Cloud Vertex AI](https://cloud.google.com/vertex-ai) - Documentação da plataforma
- [Gemini API Reference](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/gemini) - Referência dos modelos
- [Pydantic V2](https://docs.pydantic.dev/) - Validação de dados
- [Jinja2](https://jinja.palletsprojects.com/) - Engine de templates
- [Pytest](https://docs.pytest.org/) - Framework de testes
- [Tiktoken](https://github.com/openai/tiktoken) - Contagem de tokens
- [Rich](https://rich.readthedocs.io/) - Interface CLI formatada

### Artigos e Tutoriais

- [FinOps for AI/ML](https://www.finops.org/wgs/ai-ml/) - Práticas de FinOps
- [Router Pattern for LLMs](https://www.patterns.dev/posts/router-pattern/) - Padrão arquitetural
- [ADK Best Practices](https://developers.google.com/agents) - Agent Development Kit

### Custos e Pricing

- [Vertex AI Pricing](https://cloud.google.com/vertex-ai/pricing) - Preços oficiais
- [Gemini Pricing Calculator](https://cloud.google.com/products/calculator) - Calculadora de custos

---

## 📊 Métricas do Projeto

| Métrica | Valor |
|---------|-------|
| **Linhas de código** | ~1.100 (src/) |
| **Testes unitários** | 44 testes (100% passing) |
| **Cobertura** | Alta (componentes críticos) |
| **Arquivos Python** | 7 módulos + 4 de teste |
| **Configurações YAML** | 3 arquivos |
| **Templates** | 2 arquivos (Jinja2 + few-shot) |
| **Documentação** | README completo + docstrings |

---

**Versão**: 1.0.1  
**Última atualização**: Fevereiro 2026  
**Linguagem**: Python 3.8+  
**Licença**: Educacional
