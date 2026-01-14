# 🚀 Agente Adaptive Batch Processor — FinOps e Vertex AI (LAB)

## 📋 Descrição do Projeto

Este projeto é um laboratório hands-on para ensinar **FinOps** (Otimização Financeira de Operações de IA) utilizando lógica de roteamento inteligente de modelos no Google Cloud Vertex AI (simulada via mock).  
O objetivo é processar lotes de logs de erro para análise automatizada, **minimizando o custo** ao escolher dinamicamente entre dois modelos de IA, conforme o tamanho/complexidade do log.  

- **Logs simples:** modelo barato (`gemini-1.5-flash`)
- **Logs complexos:** modelo caro (`gemini-1.5-pro`)
- Relatório final mostra economia e métricas de uso — conceito fundamental de FinOps!

---

## 🏗️ Estrutura do Projeto

```
Agentes/
├── config/
│   └── adk_config.yaml       # Configuração de modelos/preços
├── data/
│   └── logs.csv              # Gerado automaticamente
├── prompts/
│   └── log_analysis.jinja2   # Template do prompt para o LLM
├── src/
│   ├── __init__.py
│   ├── log_generator.py      # Script gera logs de teste (.csv)
│   ├── processor.py          # Lógica principal do agente
│   └── token_utils.py        # Utilitários de contagem/custo
├── requirements.txt
├── run.py                    # Script principal de execução
└── README.md                 # Este arquivo
```

---

## ⚙️ Instalação e Ambiente

### Pré-requisitos
- Python **3.8** ou superior
- pip

### Instale as dependências

Abra o terminal na pasta do projeto e rode:

```bash
pip install -r requirements.txt
```

Principais pacotes usados:
- `google-cloud-aiplatform`
- `pandas`
- `jinja2`
- `rich`
- `pyyaml`

---

## 🚀 Como Rodar o Agente

### 1. Execução Recomendada (mais simples)

Basta executar:

```bash
python run.py
```

Este comando faz:
- Valida arquivos essenciais e dependências
- Gera `data/logs.csv` se não existir
- Processa automaticamente todos os logs
- Exibe no terminal uma tabela dinâmica com o progresso e, ao final, um **relatório FinOps** da economia de custos

### 2. Alternativas de Execução

**Rodar como módulo Python:**
```bash
python -m src.processor
```

**Gerar/remover apenas os logs de teste:**
```bash
python -m src.log_generator
```
Depois, processe normalmente.

---

## 🛠️ Configuração

O roteamento e preços dos modelos são definidos em `config/adk_config.yaml`.  
Exemplo:

```yaml
workers:
  junior_analyst:
    model: "gemini-1.5-flash"
    price_per_1k_input: 0.0001
    max_len_threshold: 300

  senior_engineer:
    model: "gemini-1.5-pro"
    price_per_1k_input: 0.0025
```

- **Altere modelos, preços ou limite (`max_len_threshold`)** conforme sua simulação.
- O prompt usado pelo LLM pode ser ajustado em `prompts/log_analysis.jinja2`.

---

## 🧠 Como Funciona

1. **Geração dos logs:**  
   `log_generator.py` cria um CSV com 15 logs curtos (erros simples) e 5 longos (stack traces complexos).

2. **Roteamento automático:**  
   O agente decide:
   - Log curto: usa modelo barato
   - Log longo: usa modelo caro

3. **Cálculo de custo:**  
   - Heurística rápida: 1 token ≈ 4 caracteres
   - Fórmula: `(tokens/1000) × preço_por_1k_tokens`

4. **Relatório Final:**  
   - Mostra o custo real
   - Mostra custo se tudo fosse processado no modelo caro
   - Mostra a economia obtida e percentual

---

## 📈 Exemplo de Saída

```
Adaptive Batch Processor - Log Analysis
┏━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ Log ID ┃ Length  ┃ Selected Model   ┃ Cost ($)   ┃
┡━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│      1 │      33 │ junior_analyst  │ 0.000001   │
│      2 │      25 │ junior_analyst  │ 0.000001   │
...
│     16 │     623 │ senior_engineer │ 0.000389   │
└────────┴─────────┴─────────────────┴────────────┘

╭─ FinOps Report ─────────────────────────────╮
│ Custo Total Real:     $0.001234             │
│ Custo se apenas PRO:  $0.004567             │
│ Saving (economia):     $0.003333  (73.00%)  │
╰─────────────────────────────────────────────╯
```

---

## 👨‍💻 Para Desenvolvedores: Conectar ao Vertex AI Real

Por padrão, o sistema faz *mock* dos modelos do Vertex AI.  
Para conectar ao real:
1. Configure o acesso Google Cloud:
   ```bash
   gcloud auth application-default login
   ```
2. Substitua a classe `MockVertexAI` em `src/processor.py` pela implementação real:
   ```python
   from google.cloud import aiplatform

   class RealVertexAI:
       def __init__(self, model_name: str):
           aiplatform.init(project="seu-projeto", location="us-central1")
           self.model = aiplatform.GenerativeModel(model_name)
       
       def generate(self, prompt: str):
           response = self.model.generate_content(prompt)
           return {
               "output_text": response.text,
               "model": self.model_name
           }
   ```
3. Atualize a função de construção do cliente para usar `RealVertexAI`.

---

## 🐛 Solução de Problemas

- **"ModuleNotFoundError: No module named 'src'"**  
  Rode como módulo:
  ```bash
  python -m src.processor
  ```

- **"FileNotFoundError: data/logs.csv"**  
  O arquivo é criado automaticamente. Se falhar, rode:
  ```bash
  python -m src.log_generator
  ```

- **"No module named 'yaml'"**  
  Instale as dependências:
  ```bash
  pip install -r requirements.txt
  ```

---

## 📚 Conceitos Ensinados

- FinOps (Otimização de custos em IA)
- Roteamento inteligente de modelos
- Vertex AI SDK (Google Cloud)
- Templates Jinja2 para prompts
- Métricas de custo por token

---

## 👨‍🏫 Autor

Projeto criado para o curso **Google Cloud Vertex AI SDK & ADK**.

Material educacional, livre para uso em treinamentos.

---

## 🔄 Roadmap/Futuro

- [ ] Processamento paralelo de logs
- [ ] Cache de resultados de logs já processados
- [ ] Métricas de qualidade (accuracy, latency)
- [ ] Dashboard web para visualizações
- [ ] Integração direta com Vertex AI

---
