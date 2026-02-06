"""
Script de Demonstração - Governance Gateway - Aula 01
Simula o fluxo completo de roteamento e auditoria

🎯 Objetivo da Aula 01:
Demonstrar como criar um projeto padronizado com estrutura ADK e monitorar
custos de execução em tempo real. Este script simula o problema real:
scripts soltos em Python tornam-se inauditáveis e uso indiscriminado de
modelos caros (Gemini Pro) gera desperdício financeiro invisível.

📚 Estrutura ADK (Agent Development Kit) - Aula 01:
- prompts/: Templates versionados (audit_master.jinja2)
- config/: Configurações (model_policy.yaml, safety_settings.yaml)
- tools/: Ferramentas do agente (será usado nas aulas futuras)
- src/: Código Python modular

Por que separar prompts/, tools/ e config/?
1. Versionamento: Mudanças em prompts podem ser rastreadas no Git
2. Auditoria: Configurações em YAML são auditáveis e revisáveis
3. Reutilização: Templates podem ser compartilhados entre agentes
4. Desacoplamento: Mudanças não requerem alterar código Python

Fluxo de Execução:
1. Carrega política de roteamento (YAML) - seguindo padrão ADK
2. Para cada cenário de teste:
   a. Router decide qual modelo usar (FinOps: Flash vs Pro)
   b. Simula chamada ao LLM (mock - não faz chamada real)
   c. Calcula custo estimado em tempo real
   d. Exibe resultados formatados no terminal

⚠️ IMPORTANTE - Simulação vs Produção:
Esta é uma demonstração educativa. Em produção, substitua simulate_llm_response()
por chamadas reais ao Vertex AI usando google-cloud-aiplatform.

🔮 Próximas Aulas:
- Aula 02: Adicionaremos Intent Guardrail (classificação de intenção segura)
- Aula 03: Integração real com Vertex AI e output estruturado (JSON)
"""

import json
import logging
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Tuple
from jinja2 import Template, Environment, FileSystemLoader, TemplateNotFound
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.json import JSON
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Imports do Vertex AI (condicionais - só usados se USE_MOCK=false)
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
    VERTEXAI_AVAILABLE = True
except ImportError:
    VERTEXAI_AVAILABLE = False
    import warnings
    warnings.warn(
        "Vertex AI SDK não instalado. Apenas modo simulação disponível. "
        "Instale com: pip install google-cloud-aiplatform>=1.74.0"
    )

from .router import ModelRouter
from .telemetry import CostEstimator
from .models import AuditResponse
from .exceptions import TemplateNotFoundError
from .logger import setup_logging, get_logger

# Configurar logging
logger = get_logger(__name__)

# Toggle para usar simulação (mock) ou API real do Vertex AI
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"


def render_prompt_template(user_request: str, template_path: str = "prompts/audit_master.jinja2") -> str:
    """
    Carrega e processa o template Jinja2 do prompt de auditoria.
    
    🏗️ Estrutura ADK - Aula 01:
    Templates em prompts/ permitem:
    - Versionamento de prompts no Git
    - Reutilização entre diferentes agentes
    - Mudanças sem alterar código Python
    - Auditoria de mudanças em prompts
    
    📚 Engenharia de Prompt - Aula 02:
    Na próxima aula, este template será expandido com:
    - Intent Guardrail (verificação de intenção segura)
    - Chain-of-Thought para maior precisão
    - Configuração de personas via YAML
    
    Usa Jinja2 para injetar variáveis dinamicamente no template.
    Isso permite versionamento de prompts e reutilização.
    
    Args:
        user_request: Solicitação do usuário a ser injetada no template
        template_path: Caminho relativo para o arquivo de template
        
    Returns:
        Prompt processado com variáveis substituídas
        
    Raises:
        FileNotFoundError: Se o template não for encontrado
        TemplateError: Se houver erro no processamento do template
    """
    # Resolver caminho relativo à raiz do projeto
    project_root = Path(__file__).parent.parent
    template_dir = project_root / "prompts"
    template_file = Path(template_path).name
    
    try:
        logger.debug(f"Renderizando template: {template_file}")
        # Configurar ambiente Jinja2 com FileSystemLoader
        env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Carregar e renderizar template
        template = env.get_template(template_file)
        rendered = template.render(user_request=user_request)
        logger.debug(f"Template renderizado com sucesso: {len(rendered)} caracteres")
        return rendered
    except TemplateNotFound as e:
        logger.error(f"Template não encontrado: {template_file}")
        raise TemplateNotFoundError(
            f"Template não encontrado: {template_dir / template_file}"
        ) from e
    except FileNotFoundError as e:
        logger.error(f"Diretório de templates não encontrado: {template_dir}")
        raise TemplateNotFoundError(
            f"Template não encontrado: {template_dir / template_file}"
        ) from e
    except Exception as e:
        logger.error(f"Erro ao processar template Jinja2: {e}", exc_info=True)
        raise ValueError(f"Erro ao processar template Jinja2: {e}") from e


def simulate_llm_response(model_name: str, user_request: str) -> Dict[str, Any]:
    """
    Simula a resposta do LLM sem fazer chamada real ao Vertex AI.
    
    ⚠️ IMPORTANTE - Aula 01 (Demonstração):
    Esta função SIMULA uma resposta para focar nos conceitos de:
    - Roteamento de modelos (Router-Gateway pattern)
    - Cálculo de custos (FinOps)
    - Estrutura ADK (separação de responsabilidades)
    
    🎯 Por que simulação?
    - Evita complexidade de autenticação ADC na primeira aula
    - Foca nos conceitos arquiteturais e FinOps
    - Permite demonstração sem custos reais
    
    🔮 Aula 03 - Integração Real:
    Na Aula 03, substituiremos esta função por:
    
    ```python
    from vertexai.preview.generative_models import GenerativeModel
    
    model = GenerativeModel(model_name)
    response = model.generate_content(
        prompt,
        generation_config={
            "response_mime_type": "application/json",  # Aula 03: JSON estruturado
            "temperature": 0.1
        }
    )
    
    # Aula 03: Validação robusta com Pydantic
    return AuditResponse.model_validate_json(response.text)
    ```
    
    🛡️ Aula 02 - Intent Guardrail:
    Na próxima aula, adicionaremos verificação de intenção ANTES de chamar
    o modelo, bloqueando tentativas de prompt injection e engenharia social.
    
    A simulação atual usa palavras-chave para determinar a resposta,
    simulando diferentes níveis de risco e compliance.
    
    Args:
        model_name: Nome do modelo usado (ex: 'gemini-1.5-pro-001')
        user_request: Solicitação do usuário a ser analisada
        
    Returns:
        Dicionário com a resposta simulada do auditor no formato:
        {
            "compliance_status": "APPROVED" | "REJECTED" | "REQUIRES_REVIEW",
            "risk_level": "LOW" | "MEDIUM" | "HIGH" | "CRITICAL",
            "audit_reasoning": "Texto explicativo"
        }
    """
    # ------------------------------------------------------------------------
    # Lógica de Simulação por Palavras-chave
    # ------------------------------------------------------------------------
    # Em produção, esta lógica seria substituída pela chamada real ao LLM
    # A simulação usa palavras-chave para determinar o nível de risco
    request_lower = user_request.lower()
    
    # Ordem importa: verificar exclusão antes de outras operações
    if any(word in request_lower for word in ['exclusão', 'excluir', 'delete', 'remover', 'apagar']):
        compliance = "REJECTED"
        risk = "HIGH"
        reasoning = "Operação de exclusão de dados identificada. Rejeitada por violar políticas de retenção de dados."
    elif any(word in request_lower for word in ['transfer', 'transferência', 'pix', 'pagamento']):
        compliance = "REQUIRES_REVIEW"
        risk = "MEDIUM"
        reasoning = "Operação financeira detectada. Requer revisão adicional conforme política de compliance."
    elif any(word in request_lower for word in ['consulta', 'saldo', 'extrato']):
        compliance = "APPROVED"
        risk = "LOW"
        reasoning = "Operação de consulta de baixo risco. Aprovada conforme políticas de acesso."
    else:
        compliance = "APPROVED"
        risk = "LOW"
        reasoning = "Solicitação genérica analisada. Sem riscos identificados."
    
    # ------------------------------------------------------------------------
    # Simulação de Diferença entre Modelos
    # ------------------------------------------------------------------------
    # Simula que o modelo Pro gera respostas mais detalhadas (mais tokens)
    # enquanto o Flash gera respostas mais concisas (menos tokens)
    # Isso afeta o cálculo de custos (mais tokens = maior custo)
    if 'pro' in model_name:
        # Resposta mais detalhada do Pro (simula análise mais profunda)
        reasoning += " Análise detalhada realizada com modelo avançado."
    else:
        # Resposta mais concisa do Flash (simula otimização de custos)
        reasoning = reasoning[:100] + "."
    
    return {
        "compliance_status": compliance,
        "risk_level": risk,
        "audit_reasoning": reasoning
    }


def simulate_input_output(user_request: str, model_response: Dict[str, Any]) -> tuple[int, int]:
    """
    Simula o tamanho do input e output para cálculo de custos.
    
    🎯 Aula 01 - FinOps:
    Esta função estima o tamanho do input/output para cálculo de custos.
    Em produção, estes valores viriam da API do Vertex AI que retorna
    informações sobre tokens usados na resposta.
    
    📊 Método de Estimativa:
    1. Input: Template Jinja2 renderizado + user_request
    2. Output: JSON serializado da resposta
    
    🔮 Aula 03 - Tokens Reais:
    Quando integrarmos com Vertex AI real, usaremos:
    ```python
    response.usage_metadata.prompt_token_count  # Input tokens
    response.usage_metadata.candidates_token_count  # Output tokens
    ```
    
    Por enquanto, simulamos calculando caracteres e convertendo para tokens
    usando tiktoken (método preciso) ou aproximação (fallback).
    
    Args:
        user_request: Solicitação do usuário
        model_response: Resposta do modelo (dicionário)
        
    Returns:
        Tupla (input_chars, output_chars) - número de caracteres em cada parte
    """
    # ------------------------------------------------------------------------
    # Cálculo de Input (Prompt)
    # ------------------------------------------------------------------------
    # Simula o prompt completo que seria enviado ao modelo:
    # - Template do sistema (audit_master.jinja2) processado com Jinja2
    # - Solicitação do usuário injetada dinamicamente no template
    try:
        full_prompt = render_prompt_template(user_request)
        input_chars = len(full_prompt)
    except Exception as e:
        # Fallback: se houver erro no template, usa aproximação
        input_chars = len(user_request) + 500  # Aproximação do template
    
    # ------------------------------------------------------------------------
    # Cálculo de Output (Resposta)
    # ------------------------------------------------------------------------
    # Simula a resposta JSON que o modelo retornaria
    # Em produção, este seria o texto real retornado pela API
    output_json = json.dumps(model_response, ensure_ascii=False, indent=2)
    output_chars = len(output_json)
    
    return input_chars, output_chars


def load_safety_settings() -> Dict[Any, Any]:
    """
    Carrega configurações de segurança do arquivo YAML.
    
    🛡️ Aula 03 - Safety Settings:
    As configurações de segurança definem quais tipos de conteúdo
    potencialmente prejudicial o modelo deve bloquear. Isso complementa
    o Intent Guardrail (Aula 02) que valida a pergunta do usuário.
    
    Safety Settings validam a resposta do modelo:
    - Assédio (HARASSMENT)
    - Discurso de ódio (HATE_SPEECH)
    - Conteúdo sexual explícito (SEXUALLY_EXPLICIT)
    - Conteúdo perigoso (DANGEROUS_CONTENT)
    
    Returns:
        Dicionário mapeando HarmCategory para HarmBlockThreshold
        
    Raises:
        FileNotFoundError: Se o arquivo safety_settings.yaml não existir
        ValueError: Se o YAML estiver malformado
    """
    if not VERTEXAI_AVAILABLE:
        logger.warning("Vertex AI não disponível, safety settings ignorados")
        return {}
    
    project_root = Path(__file__).parent.parent
    safety_path = project_root / "config" / "safety_settings.yaml"
    
    try:
        logger.debug(f"Carregando safety settings de: {safety_path}")
        with open(safety_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        # Mapeamento de strings YAML para enums do Vertex AI
        category_map = {
            "HARM_CATEGORY_HARASSMENT": HarmCategory.HARM_CATEGORY_HARASSMENT,
            "HARM_CATEGORY_HATE_SPEECH": HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            "HARM_CATEGORY_SEXUALLY_EXPLICIT": HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            "HARM_CATEGORY_DANGEROUS_CONTENT": HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        }
        threshold_map = {
            "BLOCK_MEDIUM_AND_ABOVE": HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            "BLOCK_LOW_AND_ABOVE": HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
            "BLOCK_ONLY_HIGH": HarmBlockThreshold.BLOCK_ONLY_HIGH,
            "BLOCK_NONE": HarmBlockThreshold.BLOCK_NONE,
        }
        
        # Converter YAML para formato esperado pela API
        safety_settings = {
            category_map[s["category"]]: threshold_map[s["threshold"]]
            for s in data["safety_settings"]
        }
        
        logger.info(f"Safety settings carregados: {len(safety_settings)} categorias configuradas")
        return safety_settings
        
    except FileNotFoundError as e:
        logger.error(f"Arquivo safety_settings.yaml não encontrado: {safety_path}")
        raise FileNotFoundError(f"Safety settings não encontrado: {safety_path}") from e
    except Exception as e:
        logger.error(f"Erro ao carregar safety settings: {e}", exc_info=True)
        raise ValueError(f"Erro ao processar safety settings: {e}") from e


def call_vertex_ai(
    model_name: str, 
    prompt: str, 
    safety_settings: Dict[Any, Any] = None
) -> Tuple[Dict[str, Any], int, int]:
    """
    Faz chamada real ao Vertex AI e retorna resposta estruturada.
    
    🔗 Aula 03 - Integração Real com Vertex AI:
    Esta função substitui simulate_llm_response() quando USE_MOCK=false.
    Faz chamada real ao Gemini 2.5 Pro/Flash via Vertex AI.
    
    Diferenças vs Simulação:
    - Usa modelo real (GenerativeModel)
    - Retorna tokens REAIS (usage_metadata)
    - Gera custos reais
    - Requer autenticação ADC
    - Valida resposta JSON com Pydantic
    
    📊 Response Estruturado:
    O parâmetro response_mime_type="application/json" força o modelo
    a retornar JSON válido, reduzindo erros de parsing e aumentando
    a confiabilidade da integração.
    
    Args:
        model_name: Nome do modelo Gemini (ex: 'gemini-2.5-pro')
        prompt: Prompt completo renderizado (com template Jinja2)
        safety_settings: Configurações de segurança (opcional)
        
    Returns:
        Tupla (resposta_dict, input_tokens, output_tokens):
        - resposta_dict: Resposta do auditor validada com Pydantic
        - input_tokens: Tokens REAIS de input (do usage_metadata)
        - output_tokens: Tokens REAIS de output (do usage_metadata)
        
    Raises:
        RuntimeError: Se Vertex AI SDK não estiver instalado
        ValueError: Se a resposta do modelo não for JSON válido
        ValidationError: Se o JSON não corresponder ao schema AuditResponse
    """
    if not VERTEXAI_AVAILABLE:
        raise RuntimeError(
            "Vertex AI SDK não disponível. Instale com: "
            "pip install google-cloud-aiplatform>=1.74.0"
        )
    
    logger.info(f"Chamando Vertex AI com modelo: {model_name}")
    
    try:
        # ------------------------------------------------------------------------
        # Passo 1: Criar instância do modelo
        # ------------------------------------------------------------------------
        # GenerativeModel é a classe principal do SDK do Vertex AI
        # Cada instância representa um modelo específico (Pro ou Flash)
        model = GenerativeModel(model_name)
        logger.debug(f"Modelo {model_name} inicializado")
        
        # ------------------------------------------------------------------------
        # Passo 2: Configurar parâmetros de geração
        # ------------------------------------------------------------------------
        # response_mime_type: Força JSON estruturado (reduz erros de parsing)
        # temperature: Controla aleatoriedade (0.1 = mais determinístico)
        generation_config = {
            "response_mime_type": "application/json",
            "temperature": 0.1
        }
        
        # ------------------------------------------------------------------------
        # Passo 3: Fazer chamada ao modelo
        # ------------------------------------------------------------------------
        # Esta é a chamada real que gera custos!
        # O Vertex AI cobra por tokens de input e output
        logger.debug("Enviando requisição para Vertex AI...")
        response = model.generate_content(
            prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )
        logger.debug("Resposta recebida do Vertex AI")
        
        # ------------------------------------------------------------------------
        # Passo 4: Extrair tokens REAIS da resposta
        # ------------------------------------------------------------------------
        # usage_metadata contém informações precisas sobre tokens consumidos
        # Isso substitui a estimativa com tiktoken usada na simulação
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        logger.info(f"Tokens consumidos: input={input_tokens}, output={output_tokens}")
        
        # ------------------------------------------------------------------------
        # Passo 5: Validar JSON com Pydantic
        # ------------------------------------------------------------------------
        # model_validate_json garante que a resposta está no formato esperado
        # Se não estiver, lança ValidationError (evita erros em produção)
        audit_response = AuditResponse.model_validate_json(response.text)
        logger.debug("Resposta validada com Pydantic")
        
        # Converter para dicionário para compatibilidade com código existente
        return audit_response.model_dump(), input_tokens, output_tokens
        
    except Exception as e:
        logger.error(f"Erro ao chamar Vertex AI: {e}", exc_info=True)
        raise


def main():
    """
    Função principal de demonstração.
    
    🎯 Aula 01 - FinOps em Tempo Real:
    Simula 3 requisições de diferentes departamentos para demonstrar:
    - Roteamento baseado em tier (platinum, standard, budget)
    - Cálculo de custos em tempo real
    - Comparação Flash vs Pro
    
    📚 Conexão com próximas aulas:
    - Aula 02: Cada requisição será validada por Intent Guardrail
    - Aula 03: Substituiremos simulação por chamadas reais ao Vertex AI
    """
    # Configurar logging para a aplicação
    setup_logging(level="INFO")
    
    # Log do modo de operação
    mode_str = "SIMULAÇÃO (Mock)" if USE_MOCK else "PRODUÇÃO (Vertex AI Real)"
    logger.info(f"Iniciando Governance Gateway - Modo: {mode_str}")
    
    console = Console()
    
    # ------------------------------------------------------------------------
    # Inicialização do Vertex AI (apenas se USE_MOCK=false)
    # ------------------------------------------------------------------------
    # Application Default Credentials (ADC) são usadas automaticamente
    # Certifique-se de executar: gcloud auth application-default login
    if not USE_MOCK:
        if not VERTEXAI_AVAILABLE:
            console.print("[bold red]ERRO: Vertex AI SDK não instalado![/bold red]")
            console.print("Instale com: pip install google-cloud-aiplatform>=1.74.0")
            console.print("Ou defina USE_MOCK=true no arquivo .env para usar simulação")
            return
        
        try:
            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-east1")
            
            if not project_id:
                console.print("[bold red]ERRO: GOOGLE_CLOUD_PROJECT não definido no .env[/bold red]")
                console.print("Configure o arquivo .env com seu Project ID do GCP")
                return
            
            logger.info(f"Inicializando Vertex AI: project={project_id}, location={location}")
            vertexai.init(project=project_id, location=location)
            logger.info("Vertex AI inicializado com sucesso")
            
            # Carregar safety settings
            safety_settings = load_safety_settings()
            
        except Exception as e:
            console.print(f"[bold red]Erro ao inicializar Vertex AI: {e}[/bold red]")
            console.print("Verifique:")
            console.print("1. GOOGLE_CLOUD_PROJECT está correto no .env")
            console.print("2. Executou: gcloud auth application-default login")
            console.print("3. Tem permissões no projeto GCP")
            logger.error(f"Erro na inicialização: {e}", exc_info=True)
            return
    else:
        safety_settings = {}
        logger.info("Modo simulação ativado - sem conexão com Vertex AI")
    
    # Título
    console.print("\n")
    mode_badge = "[yellow]SIMULAÇÃO[/yellow]" if USE_MOCK else "[green]PRODUÇÃO[/green]"
    console.print(
        Panel.fit(
            f"[bold cyan]Governance Gateway[/bold cyan] {mode_badge}\n"
            "[dim]Sistema de Roteamento de Modelos LLM - Padrão Router-Gateway[/dim]",
            border_style="cyan"
        )
    )
    console.print("\n")
    
    # ------------------------------------------------------------------------
    # Inicialização dos Componentes
    # ------------------------------------------------------------------------
    # Router: Carrega política YAML e decide qual modelo usar
    # CostEstimator: Carrega preços YAML e calcula custos
    try:
        logger.info("Inicializando componentes: ModelRouter e CostEstimator")
        router = ModelRouter()
        cost_estimator = CostEstimator()
        logger.info("Componentes inicializados com sucesso")
    except Exception as e:
        logger.error(f"Erro ao inicializar componentes: {e}", exc_info=True)
        console.print(f"[bold red]Erro ao inicializar componentes: {e}[/bold red]")
        return
    
    # ------------------------------------------------------------------------
    # Cenários de Teste
    # ------------------------------------------------------------------------
    # Simula requisições de 3 departamentos diferentes para demonstrar
    # o roteamento baseado em tier e complexidade
    scenarios = [
        {
            "department": "legal_dept",
            "department_name": "Departamento Jurídico",
            "user_request": "Preciso revisar o contrato de parceria com a empresa XYZ para verificar cláusulas de confidencialidade",
            "complexity": 0.8
        },
        {
            "department": "hr_dept",
            "department_name": "Recursos Humanos",
            "user_request": "Verificar saldo de férias do funcionário ID 12345",
            "complexity": 0.3
        },
        {
            "department": "it_ops",
            "department_name": "Operações de TI",
            "user_request": "Consultar logs de acesso do sistema de gestão",
            "complexity": 0.2
        }
    ]
    
    # ------------------------------------------------------------------------
    # Processamento de Cada Cenário
    # ------------------------------------------------------------------------
    for idx, scenario in enumerate(scenarios, 1):
        console.print(f"\n[bold yellow]--- Cenario {idx}: {scenario['department_name']} ---[/bold yellow]\n")
        
        # --------------------------------------------------------------------
        # Passo 1: Roteamento (Decisão do Modelo)
        # --------------------------------------------------------------------
        # O router consulta a política YAML e decide qual modelo usar
        # baseado no tier do departamento e na complexidade da requisição
        try:
            logger.info(f"Processando cenário {idx}: {scenario['department_name']}")
            selected_model = router.route_request(
                scenario['department'],
                scenario['complexity']
            )
            logger.debug(f"Modelo selecionado: {selected_model}")
        except Exception as e:
            logger.error(f"Erro no roteamento para {scenario['department']}: {e}", exc_info=True)
            console.print(f"[bold red]Erro no roteamento: {e}[/bold red]")
            continue
        
        # --------------------------------------------------------------------
        # Passo 2: Chamada ao LLM (Mock ou Real)
        # --------------------------------------------------------------------
        # Toggle USE_MOCK determina se usa simulação ou API real
        try:
            if USE_MOCK:
                # Modo simulação: usa keyword matching (sem custos reais)
                logger.debug("Usando simulação (mock)")
                response_data = simulate_llm_response(
                    selected_model,
                    scenario['user_request']
                )
                
                # Simula tamanho do input/output para cálculo de custos
                input_chars, output_chars = simulate_input_output(
                    scenario['user_request'],
                    response_data
                )
                
                # Calcula custo estimado (baseado em caracteres)
                estimated_cost = cost_estimator.calculate_cost(
                    selected_model,
                    input_chars,
                    output_chars
                )
                
            else:
                # Modo produção: usa Vertex AI real (gera custos reais)
                logger.debug("Usando Vertex AI real")
                
                # Renderizar prompt completo com template Jinja2
                prompt = render_prompt_template(scenario['user_request'])
                
                # Fazer chamada real ao Vertex AI
                response_data, input_tokens, output_tokens = call_vertex_ai(
                    selected_model,
                    prompt,
                    safety_settings
                )
                
                # Calcula custo real (baseado em tokens exatos da API)
                estimated_cost = cost_estimator.calculate_cost_from_tokens(
                    selected_model,
                    input_tokens,
                    output_tokens
                )
            
            logger.info(f"Custo calculado: ${estimated_cost:.6f} USD")
            
        except Exception as e:
            logger.error(f"Erro ao processar requisição: {e}", exc_info=True)
            console.print(f"[bold red]Erro ao processar requisição: {e}[/bold red]")
            continue
        
        # --------------------------------------------------------------------
        # Passo 3: Exibição de Resultados
        # --------------------------------------------------------------------
        # Usa a biblioteca Rich para criar tabelas e painéis formatados
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Atributo", style="cyan", width=25)
        table.add_column("Valor", style="white")
        
        table.add_row("Departamento", scenario['department_name'])
        table.add_row("Complexidade", f"{scenario['complexity']:.2f}")
        table.add_row("Modelo Escolhido", f"[bold green]{selected_model}[/bold green]")
        table.add_row("Custo Estimado", f"[bold yellow]${estimated_cost:.6f} USD[/bold yellow]")
        
        # Mostrar tokens ou chars dependendo do modo
        if USE_MOCK:
            table.add_row("Input (chars)", str(input_chars))
            table.add_row("Output (chars)", str(output_chars))
        else:
            table.add_row("Input (tokens)", str(input_tokens))
            table.add_row("Output (tokens)", str(output_tokens))
        
        console.print(table)
        
        # Exibir resposta do auditor em formato JSON formatado
        console.print("\n[bold]Resposta do Auditor:[/bold]")
        console.print(JSON(json.dumps(response_data, ensure_ascii=False, indent=2)))
        
        console.print("\n")
    
    # ------------------------------------------------------------------------
    # Resumo Final
    # ------------------------------------------------------------------------
    logger.info("Demonstração concluída com sucesso")
    console.print(
        Panel.fit(
            "[bold green]OK - Demonstracao concluida com sucesso![/bold green]\n"
            "[dim]O sistema demonstrou o roteamento baseado em politica YAML[/dim]",
            border_style="green"
        )
    )
    console.print("\n")


if __name__ == "__main__":
    main()
