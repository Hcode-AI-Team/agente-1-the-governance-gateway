"""
Script de Demonstração - Governance Gateway
Simula o fluxo completo de roteamento e auditoria

Este é o ponto de entrada do sistema. Demonstra o padrão Router-Gateway
simulando requisições de diferentes departamentos e exibindo:
- Modelo escolhido pelo router
- Custo estimado da operação (FinOps)
- Resposta simulada do auditor de governança

Fluxo de Execução:
1. Carrega política de roteamento (YAML)
2. Para cada cenário de teste:
   a. Router decide qual modelo usar
   b. Simula chamada ao LLM (mock - não faz chamada real)
   c. Calcula custo estimado
   d. Exibe resultados formatados no terminal

Nota: Esta é uma demonstração. Em produção, substitua simulate_llm_response()
por chamadas reais ao Vertex AI usando google-cloud-aiplatform.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any
from jinja2 import Template, Environment, FileSystemLoader, TemplateNotFound
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.json import JSON

from src.router import ModelRouter
from src.telemetry import CostEstimator
from src.models import AuditResponse
from src.exceptions import TemplateNotFoundError
from src.logger import setup_logging, get_logger

# Configurar logging
logger = get_logger(__name__)


def render_prompt_template(user_request: str, template_path: str = "prompts/audit_master.jinja2") -> str:
    """
    Carrega e processa o template Jinja2 do prompt de auditoria.
    
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
    
    IMPORTANTE: Esta é uma função de demonstração. Em produção, substitua por:
    
    ```python
    from vertexai.preview.generative_models import GenerativeModel
    
    model = GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return parse_json_response(response.text)
    ```
    
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
    
    Em produção, estes valores viriam da API do Vertex AI que retorna
    informações sobre tokens usados. Aqui simulamos calculando caracteres.
    
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


def main():
    """
    Função principal de demonstração.
    Simula 3 requisições de diferentes departamentos e exibe os resultados.
    """
    # Configurar logging para a aplicação
    setup_logging(level="INFO")
    logger.info("Iniciando Governance Gateway - Demonstração")
    
    console = Console()
    
    # Título
    console.print("\n")
    console.print(
        Panel.fit(
            "[bold cyan]Governance Gateway[/bold cyan]\n"
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
        console.print(f"\n[bold yellow]━━━ Cenário {idx}: {scenario['department_name']} ━━━[/bold yellow]\n")
        
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
        # Passo 2: Simulação de Chamada ao LLM
        # --------------------------------------------------------------------
        # Em produção, aqui seria feita a chamada real ao Vertex AI
        # com o modelo selecionado e o prompt formatado
        mock_response = simulate_llm_response(
            selected_model,
            scenario['user_request']
        )
        
        # --------------------------------------------------------------------
        # Passo 3: Cálculo de Custos (FinOps)
        # --------------------------------------------------------------------
        # Simula tamanho do input/output e calcula custo estimado
        # Em produção, os tokens viriam da resposta da API do Vertex AI
        input_chars, output_chars = simulate_input_output(
            scenario['user_request'],
            mock_response
        )
        
        try:
            estimated_cost = cost_estimator.calculate_cost(
                selected_model,
                input_chars,
                output_chars
            )
            logger.debug(f"Custo estimado: ${estimated_cost:.6f} USD")
        except Exception as e:
            logger.error(f"Erro no cálculo de custo: {e}", exc_info=True)
            console.print(f"[bold red]Erro no cálculo de custo: {e}[/bold red]")
            continue
        
        # --------------------------------------------------------------------
        # Passo 4: Exibição de Resultados
        # --------------------------------------------------------------------
        # Usa a biblioteca Rich para criar tabelas e painéis formatados
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Atributo", style="cyan", width=25)
        table.add_column("Valor", style="white")
        
        table.add_row("Departamento", scenario['department_name'])
        table.add_row("Complexidade", f"{scenario['complexity']:.2f}")
        table.add_row("Modelo Escolhido", f"[bold green]{selected_model}[/bold green]")
        table.add_row("Custo Estimado", f"[bold yellow]${estimated_cost:.6f} USD[/bold yellow]")
        table.add_row("Input (chars)", str(input_chars))
        table.add_row("Output (chars)", str(output_chars))
        
        console.print(table)
        
        # Exibir resposta do auditor em formato JSON formatado
        console.print("\n[bold]Resposta do Auditor:[/bold]")
        console.print(JSON(json.dumps(mock_response, ensure_ascii=False, indent=2)))
        
        console.print("\n")
    
    # ------------------------------------------------------------------------
    # Resumo Final
    # ------------------------------------------------------------------------
    logger.info("Demonstração concluída com sucesso")
    console.print(
        Panel.fit(
            "[bold green]✓ Demonstração concluída com sucesso![/bold green]\n"
            "[dim]O sistema demonstrou o roteamento baseado em política YAML[/dim]",
            border_style="green"
        )
    )
    console.print("\n")


if __name__ == "__main__":
    main()

