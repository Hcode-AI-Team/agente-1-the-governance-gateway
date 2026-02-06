# Guia de Migração: Vertex AI com Gemini 2.5

Este documento descreve todas as mudanças realizadas para migrar o projeto da simulação mock para integração real com o Vertex AI usando os modelos Gemini 2.5 Pro e Gemini 2.5 Flash.

## 📋 Índice

- [Visão Geral das Mudanças](#visão-geral-das-mudanças)
- [Passo a Passo da Implementação](#passo-a-passo-da-implementação)
- [Como Usar](#como-usar)
- [Configuração do GCP](#configuração-do-gcp)
- [Toggle Mock/Produção](#toggle-mockprodução)
- [Diferenças entre Modos](#diferenças-entre-modos)
- [Troubleshooting](#troubleshooting)

---

## Visão Geral das Mudanças

### O que mudou?

1. **Modelos atualizados**: Gemini 1.5 → Gemini 2.5
2. **Integração real com Vertex AI**: Adicionada função `call_vertex_ai()` que faz chamadas reais à API
3. **Toggle Mock/Produção**: Variável `USE_MOCK` permite alternar entre simulação e API real
4. **Tokens reais**: Novo método `calculate_cost_from_tokens()` usa tokens exatos da API
5. **Safety Settings**: Configurações de segurança agora são aplicadas nas chamadas reais
6. **Autenticação ADC**: Suporte para Application Default Credentials do Google Cloud

### Arquitetura Atualizada

```
┌─────────────────┐
│   main.py       │
│  (orchestrator) │
└────────┬────────┘
         │
    ┌────▼─────┐
    │ USE_MOCK?│
    └────┬─────┘
         │
    ┌────▼───────────────────────┐
    │ TRUE          │ FALSE       │
    │ simulação     │ produção    │
    └────┬──────────┴─────┬───────┘
         │                │
    ┌────▼─────┐    ┌─────▼──────────┐
    │ simulate │    │ call_vertex_ai()│
    │ _llm_    │    │                 │
    │ response │    │ GenerativeModel │
    └────┬─────┘    └─────┬──────────┘
         │                │
         │           ┌────▼──────────┐
         │           │ usage_metadata│
         │           │ (tokens reais)│
         │           └────┬──────────┘
         │                │
    ┌────▼────────────────▼──┐
    │   CostEstimator        │
    │ - calculate_cost()      │
    │ - calculate_cost_from_  │
    │   tokens() ⭐ NOVO      │
    └─────────────────────────┘
```

---

## Passo a Passo da Implementação

### Passo 0: Autenticação no Google Cloud (Pré-requisito)

Antes de usar o modo produção, configure a autenticação:

```bash
# 1. Instalar o Google Cloud CLI
# Download em: https://cloud.google.com/sdk/docs/install

# 2. Fazer login no GCP
gcloud auth login

# 3. Configurar Application Default Credentials (ADC)
gcloud auth application-default login

# 4. Definir o projeto padrão
gcloud config set project SEU_PROJECT_ID
```

**Importante**: A autenticação ADC é necessária APENAS para o modo produção (USE_MOCK=false).

### Passo 1: Arquivo `.env`

Criado arquivo `.env` na raiz do projeto:

```env
# Google Cloud Project ID
GOOGLE_CLOUD_PROJECT=seu-project-id-aqui

# Região do Vertex AI (ex: us-central1, us-east1)
GOOGLE_CLOUD_LOCATION=us-east1

# Toggle: true = simulação, false = API real
USE_MOCK=true
```

**Segurança**: O arquivo `.env` foi adicionado ao `.gitignore` e não deve ser versionado.

### Passo 2: Dependências Atualizadas

Arquivo `requirements.txt` foi atualizado:

```txt
google-cloud-aiplatform>=1.74.0   # Suporte Gemini 2.5
python-dotenv>=1.0.0               # Carregar variáveis do .env
```

Instalar com:

```bash
pip install -r requirements.txt
```

### Passo 3: Modelos Atualizados

#### `config/model_policy.yaml`

Nomes dos modelos atualizados:

```yaml
departments:
  legal_dept:
    model: gemini-2.5-pro      # Era: gemini-1.5-pro-001
  
  it_ops:
    model: gemini-2.5-flash    # Era: gemini-1.5-flash-001

pricing:
  gemini-2.5-pro:
    input_per_1k_tokens: 0.00125
    output_per_1k_tokens: 0.01000
  
  gemini-2.5-flash:
    input_per_1k_tokens: 0.000150
    output_per_1k_tokens: 0.000600
```

### Passo 4: Validação Pydantic

#### `src/models.py`

Lista de modelos válidos atualizada:

```python
valid_models = ['gemini-2.5-pro', 'gemini-2.5-flash']
```

### Passo 5: Router Atualizado

#### `src/router.py`

Nomes hardcoded dos modelos atualizados em 4 locais:

- Tier platinum: `'gemini-2.5-pro'`
- Tier budget: `'gemini-2.5-flash'`
- Tier standard (baixa complexidade): `'gemini-2.5-flash'`
- Tier standard (alta complexidade): `'gemini-2.5-pro'`

### Passo 6: Integração com Vertex AI

#### `src/main.py`

**Novos imports**:

```python
import os
import yaml
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
```

**Nova função `load_safety_settings()`**:

Carrega configurações do `config/safety_settings.yaml` e converte para enums do Vertex AI.

**Nova função `call_vertex_ai()`**:

```python
def call_vertex_ai(model_name: str, prompt: str, safety_settings: Dict) -> Tuple[Dict, int, int]:
    """
    Faz chamada real ao Vertex AI.
    
    Returns:
        Tupla (resposta_dict, input_tokens, output_tokens)
    """
    model = GenerativeModel(model_name)
    
    response = model.generate_content(
        prompt,
        generation_config={
            "response_mime_type": "application/json",
            "temperature": 0.1
        },
        safety_settings=safety_settings
    )
    
    # Extrair tokens REAIS
    input_tokens = response.usage_metadata.prompt_token_count
    output_tokens = response.usage_metadata.candidates_token_count
    
    # Validar JSON com Pydantic
    audit_response = AuditResponse.model_validate_json(response.text)
    
    return audit_response.model_dump(), input_tokens, output_tokens
```

**Função `main()` atualizada**:

- Inicializa Vertex AI se `USE_MOCK=false`
- Carrega safety settings
- Toggle para escolher entre simulação e API real
- Exibe tokens reais quando em modo produção

### Passo 7: Cálculo de Custos com Tokens Reais

#### `src/telemetry.py`

**Novo método `calculate_cost_from_tokens()`**:

```python
def calculate_cost_from_tokens(
    self,
    model_name: str,
    input_tokens: int,
    output_tokens: int
) -> float:
    """
    Calcula custo usando tokens REAIS da API (100% preciso).
    """
    model_pricing = self.pricing[model_name]
    input_cost = (input_tokens / 1000.0) * model_pricing.input_per_1k_tokens
    output_cost = (output_tokens / 1000.0) * model_pricing.output_per_1k_tokens
    return round(input_cost + output_cost, 6)
```

### Passo 8: Safety Settings

As configurações de `config/safety_settings.yaml` agora são:

- Carregadas pela função `load_safety_settings()`
- Convertidas para enums do Vertex AI
- Aplicadas na chamada ao `GenerativeModel.generate_content()`

### Passo 9: Testes Atualizados

Todos os testes foram atualizados:

- **`tests/test_router.py`**: Nomes de modelos atualizados em 9 asserts
- **`tests/test_telemetry.py`**: Nomes atualizados + 5 novos testes para `calculate_cost_from_tokens()`
- **`tests/test_models.py`**: Nomes atualizados + validação de pricing

**Novos testes adicionados**:

- `test_calculate_cost_from_tokens_pro()`: Testa cálculo com tokens reais para Pro
- `test_calculate_cost_from_tokens_flash()`: Testa cálculo com tokens reais para Flash
- `test_calculate_cost_from_tokens_invalid_model()`: Testa erro com modelo inválido
- `test_calculate_cost_from_tokens_zero_values()`: Testa edge case com tokens zero
- `test_calculate_cost_from_tokens_precision()`: Testa precisão de 6 casas decimais

---

## Como Usar

### Modo Simulação (Padrão)

```bash
# 1. Configure o .env (ou deixe o padrão)
echo "USE_MOCK=true" > .env

# 2. Execute
python main.py
```

**Sem autenticação necessária. Sem custos.**

### Modo Produção (API Real)

```bash
# 1. Configure autenticação (apenas primeira vez)
gcloud auth application-default login

# 2. Configure o .env
cat > .env << EOF
GOOGLE_CLOUD_PROJECT=seu-project-id
GOOGLE_CLOUD_LOCATION=us-east1
USE_MOCK=false
EOF

# 3. Execute
python main.py
```

**⚠️ ATENÇÃO: Gera custos reais no GCP!**

---

## Configuração do GCP

### 1. Criar Projeto no GCP

```bash
gcloud projects create fiap-bv-ia-2025 --name="FIAP BV IA 2025"
gcloud config set project fiap-bv-ia-2025
```

### 2. Habilitar APIs Necessárias

```bash
gcloud services enable aiplatform.googleapis.com
```

### 3. Configurar Billing

O projeto precisa ter billing habilitado para usar o Vertex AI:

1. Acesse: https://console.cloud.google.com/billing
2. Vincule um billing account ao projeto

### 4. Permissões Necessárias

Sua conta precisa das seguintes roles:

- `roles/aiplatform.user` - Usar o Vertex AI
- `roles/serviceusage.serviceUsageConsumer` - Consumir APIs

```bash
gcloud projects add-iam-policy-binding fiap-bv-ia-2025 \
    --member="user:seu-email@gmail.com" \
    --role="roles/aiplatform.user"
```

---

## Toggle Mock/Produção

### Como funciona o toggle?

A variável `USE_MOCK` no arquivo `.env` controla o comportamento:

```python
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"

if USE_MOCK:
    # Usa simulate_llm_response() - sem custos
    response_data = simulate_llm_response(model_name, user_request)
else:
    # Usa call_vertex_ai() - API real com custos
    response_data, input_tokens, output_tokens = call_vertex_ai(model_name, prompt)
```

### Quando usar cada modo?

| Modo       | Quando usar                                  | Requer Auth | Gera Custos |
| ---------- | -------------------------------------------- | ----------- | ----------- |
| Simulação  | Desenvolvimento, testes, aulas, demos        | ❌ Não      | ❌ Não      |
| Produção   | Produção, validação real, benchmark de custos| ✅ Sim      | ✅ Sim      |

---

## Diferenças entre Modos

### Simulação (USE_MOCK=true)

**Vantagens**:
- ✅ Sem autenticação necessária
- ✅ Sem custos
- ✅ Rápido (sem latência de rede)
- ✅ Determinístico (sempre mesma resposta)

**Limitações**:
- ❌ Respostas baseadas em keywords (não usa IA real)
- ❌ Tokens estimados (aproximação com tiktoken)
- ❌ Não valida integração real com Vertex AI

**Casos de uso**:
- Desenvolvimento local
- Testes unitários
- Demonstrações em aula
- CI/CD pipeline

### Produção (USE_MOCK=false)

**Vantagens**:
- ✅ Usa IA real (Gemini 2.5 Pro/Flash)
- ✅ Respostas inteligentes e contextuais
- ✅ Tokens EXATOS da API (100% preciso)
- ✅ Validação JSON estruturado
- ✅ Safety settings aplicados

**Limitações**:
- ❌ Requer autenticação ADC
- ❌ Gera custos reais no GCP
- ❌ Latência de rede (500-2000ms por chamada)
- ❌ Sujeito a rate limits da API

**Casos de uso**:
- Validação de integração
- Testes de aceitação
- Benchmark de custos
- Produção

---

## Troubleshooting

### Erro: "Vertex AI SDK não instalado"

**Causa**: Biblioteca `google-cloud-aiplatform` não instalada.

**Solução**:
```bash
pip install google-cloud-aiplatform>=1.74.0
```

### Erro: "GOOGLE_CLOUD_PROJECT não definido"

**Causa**: Arquivo `.env` não configurado ou variável ausente.

**Solução**:
```bash
echo "GOOGLE_CLOUD_PROJECT=seu-project-id" >> .env
```

### Erro: "Could not automatically determine credentials"

**Causa**: Application Default Credentials não configuradas.

**Solução**:
```bash
gcloud auth application-default login
```

### Erro: "Permission denied on resource project"

**Causa**: Conta não tem permissões no projeto GCP.

**Solução**:
```bash
gcloud projects add-iam-policy-binding SEU_PROJECT_ID \
    --member="user:seu-email@gmail.com" \
    --role="roles/aiplatform.user"
```

### Erro: "API [aiplatform.googleapis.com] not enabled"

**Causa**: API do Vertex AI não habilitada no projeto.

**Solução**:
```bash
gcloud services enable aiplatform.googleapis.com
```

### Erro: "Modelo não encontrado na política"

**Causa**: Nome do modelo no YAML não corresponde ao esperado.

**Solução**: Verifique se `config/model_policy.yaml` usa:
- `gemini-2.5-pro` (não `gemini-1.5-pro-001`)
- `gemini-2.5-flash` (não `gemini-1.5-flash-001`)

### Performance: Chamadas muito lentas

**Causa**: Latência de rede para API do Vertex AI.

**Soluções**:
1. Use região `GOOGLE_CLOUD_LOCATION` mais próxima
2. Configure timeout adequado
3. Considere caching de respostas
4. Use batch processing quando possível

---

## Comparação de Custos (Gemini 2.5)

### Pricing (valores de referência)

| Modelo            | Input ($/1k tokens) | Output ($/1k tokens) | Uso recomendado       |
| ----------------- | ------------------- | -------------------- | --------------------- |
| gemini-2.5-pro    | $0.00125            | $0.01000             | Tarefas complexas     |
| gemini-2.5-flash  | $0.00015            | $0.00060             | Tarefas simples       |

### Exemplo de Custos

**Cenário**: 1000 tokens input, 500 tokens output

```
Pro:
  Input:  (1000/1000) * $0.00125 = $0.00125
  Output: (500/1000)  * $0.01000 = $0.00500
  Total:  $0.00625

Flash:
  Input:  (1000/1000) * $0.00015 = $0.00015
  Output: (500/1000)  * $0.00060 = $0.00030
  Total:  $0.00045

Economia: $0.00625 - $0.00045 = $0.00580 (92.8% mais barato!)
```

### Calculadora de ROI

Para 1.000.000 de requisições/mês:

```
Se usar apenas Pro:
  1M requisições * $0.00625 = $6,250/mês

Se usar Router-Gateway (50% Flash, 50% Pro):
  500k * $0.00045 + 500k * $0.00625 = $3,350/mês
  
Economia anual: $34,800
```

---

## Checklist de Validação

Antes de usar em produção, valide:

- [ ] Autenticação ADC configurada
- [ ] Variável `GOOGLE_CLOUD_PROJECT` correta
- [ ] API `aiplatform.googleapis.com` habilitada
- [ ] Permissões IAM configuradas
- [ ] Billing account vinculado ao projeto
- [ ] Testes passando (`pytest tests/`)
- [ ] Arquivo `.env` configurado
- [ ] Safety settings revisadas
- [ ] Política de roteamento ajustada
- [ ] Monitoramento de custos configurado

---

## Próximos Passos

### Melhorias Sugeridas

1. **Caching de Respostas**: Implementar Redis para cache de respostas frequentes
2. **Rate Limiting**: Adicionar controle de taxa para evitar rate limits
3. **Async/Await**: Refatorar para chamadas assíncronas (maior throughput)
4. **Batch Processing**: Processar múltiplas requisições em paralelo
5. **Monitoramento**: Integrar com Cloud Monitoring para dashboards
6. **Alertas**: Configurar alertas de custo no GCP
7. **Retry Logic**: Implementar retry com backoff exponencial
8. **Circuit Breaker**: Adicionar circuit breaker para failover

### Aulas Futuras

- **Aula 02**: Intent Guardrail (validação de segurança)
- **Aula 03**: Output estruturado e validação avançada
- **Aula 04**: Integração com ferramentas (Function Calling)
- **Aula 05**: Deployment em produção (Cloud Run)

---

## Referências

- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Gemini API Reference](https://cloud.google.com/vertex-ai/docs/generative-ai/model-reference/gemini)
- [Vertex AI Pricing](https://cloud.google.com/vertex-ai/pricing)
- [Application Default Credentials](https://cloud.google.com/docs/authentication/application-default-credentials)
- [Safety Settings](https://cloud.google.com/vertex-ai/docs/generative-ai/learn/responsible-ai)

---

**Versão**: 2.0 (Gemini 2.5)  
**Data**: 2026-02-06  
**Status**: ✅ Implementação completa
