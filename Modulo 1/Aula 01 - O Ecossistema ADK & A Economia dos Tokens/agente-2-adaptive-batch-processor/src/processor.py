from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd
import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape, TemplateNotFound
from rich import box
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.panel import Panel

# Suporte para execução direta (imports absolutos) e como módulo (imports relativos)
try:
    from .log_generator import generate_logs, LOGS_CSV_PATH
    from .token_utils import estimate_cost
except ImportError:
    # Fallback para execução direta
    from src.log_generator import generate_logs, LOGS_CSV_PATH
    from src.token_utils import estimate_cost


BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "adk_config.yaml"
PROMPTS_DIR = BASE_DIR / "prompts"
PROMPT_TEMPLATE_NAME = "log_analysis.jinja2"

console = Console()


class MockVertexAI:
    """
    Mock simples de um cliente Vertex AI para este laboratório.

    Esta classe simula a latência e uma resposta textual fixa, sem
    fazer chamadas reais à API do Google Cloud.

    ONDE CONECTAR AO VERTEX AI REAL:
    - Em um cenário real, você poderia:
        from google.cloud import aiplatform
        aiplatform.init(project="seu-projeto", location="us-central1")
        model = aiplatform.GenerativeModel(model_name)
        response = model.generate_content(prompt)
    - Aqui, apenas simulamos o comportamento para fins didáticos.
    """

    def __init__(self, model_name: str, latency_seconds: float) -> None:
        self.model_name = model_name
        self.latency_seconds = latency_seconds

    def generate(self, prompt: str) -> Dict[str, Any]:
        # Simula tempo de inferência diferente por modelo
        time.sleep(self.latency_seconds)

        # Em um cenário real, aqui retornaríamos a saída do modelo Gemini
        return {
            "output_text": "ANALYSIS_DONE",
            "latency_seconds": self.latency_seconds,
            "model": self.model_name,
        }


def load_config(path: Path = CONFIG_PATH) -> Dict[str, Any]:
    """
    Carrega e valida o arquivo de configuração YAML.
    
    Raises
    ------
    FileNotFoundError
        Se o arquivo de configuração não existir.
    yaml.YAMLError
        Se o arquivo YAML estiver malformado.
    ValueError
        Se a estrutura do config estiver inválida.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de configuração não encontrado: {path}\n"
            f"Certifique-se de que o arquivo existe em: {path.absolute()}"
        )
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(
            f"Erro ao ler arquivo YAML {path}: {e}\n"
            "Verifique se o arquivo está bem formatado."
        ) from e
    
    # Validação básica da estrutura
    if not config:
        raise ValueError(f"Arquivo de configuração vazio: {path}")
    
    if "workers" not in config:
        raise ValueError(
            f"Chave 'workers' não encontrada no arquivo de configuração: {path}"
        )
    
    required_workers = ["junior_analyst", "senior_engineer"]
    for worker_name in required_workers:
        if worker_name not in config["workers"]:
            raise ValueError(
                f"Worker '{worker_name}' não encontrado na configuração. "
                f"Workers disponíveis: {list(config['workers'].keys())}"
            )
        
        worker_cfg = config["workers"][worker_name]
        if "model" not in worker_cfg:
            raise ValueError(
                f"Worker '{worker_name}' não possui a chave 'model' na configuração"
            )
        if "price_per_1k_input" not in worker_cfg:
            raise ValueError(
                f"Worker '{worker_name}' não possui a chave 'price_per_1k_input' na configuração"
            )
    
    return config


def build_prompt_env() -> Environment:
    """
    Cria o ambiente Jinja2 para carregar templates.
    
    Raises
    ------
    FileNotFoundError
        Se o diretório de prompts não existir.
    """
    if not PROMPTS_DIR.exists():
        raise FileNotFoundError(
            f"Diretório de prompts não encontrado: {PROMPTS_DIR}\n"
            f"Certifique-se de que o diretório existe em: {PROMPTS_DIR.absolute()}"
        )
    
    env = Environment(
        loader=FileSystemLoader(str(PROMPTS_DIR)),
        autoescape=select_autoescape(enabled_extensions=("jinja2",)),
    )
    return env


def select_worker_for_log(
    log_message: str, config: Dict[str, Any]
) -> Tuple[str, Dict[str, Any]]:
    """
    Aplica a regra de roteamento:
    - Se o tamanho do log (em caracteres) for maior que max_len_threshold do junior,
      usa o worker senior; caso contrário, usa o junior.
    
    Raises
    ------
    ValueError
        Se a configuração estiver inválida ou o log_message for None.
    """
    if log_message is None:
        raise ValueError("log_message não pode ser None")
    
    try:
        workers = config["workers"]
        junior_cfg = workers["junior_analyst"]
        senior_cfg = workers["senior_engineer"]

        threshold = int(junior_cfg.get("max_len_threshold", 300))
        log_len = len(log_message or "")

        if log_len > threshold:
            return "senior_engineer", senior_cfg
        return "junior_analyst", junior_cfg
    except KeyError as e:
        raise ValueError(
            f"Erro ao acessar configuração de workers: {e}\n"
            "Verifique se o arquivo de configuração está correto."
        ) from e


def build_mock_client(model_name: str) -> MockVertexAI:
    """
    Retorna um MockVertexAI com diferentes latências para cada modelo.

    - gemini-1.5-flash  -> latência baixa
    - gemini-1.5-pro    -> latência maior
    """
    if "flash" in model_name:
        latency = 0.05
    else:
        latency = 0.20
    return MockVertexAI(model_name=model_name, latency_seconds=latency)


def validate_files() -> Tuple[bool, list[str]]:
    """
    Valida se todos os arquivos necessários existem antes de processar.
    
    Returns
    -------
    Tuple[bool, list[str]]
        Tupla contendo:
        - bool: True se todos os arquivos críticos existem, False caso contrário
        - list[str]: Lista de mensagens de erro/aviso (vazia se tudo estiver OK)
    """
    errors = []
    
    # Valida arquivo de configuração
    if not CONFIG_PATH.exists():
        errors.append(
            f"❌ Arquivo de configuração não encontrado: {CONFIG_PATH}\n"
            f"   Caminho esperado: {CONFIG_PATH.absolute()}"
        )
    
    # Valida diretório de prompts
    if not PROMPTS_DIR.exists():
        errors.append(
            f"❌ Diretório de prompts não encontrado: {PROMPTS_DIR}\n"
            f"   Caminho esperado: {PROMPTS_DIR.absolute()}"
        )
    else:
        # Valida template específico
        template_path = PROMPTS_DIR / PROMPT_TEMPLATE_NAME
        if not template_path.exists():
            errors.append(
                f"❌ Template não encontrado: {PROMPT_TEMPLATE_NAME}\n"
                f"   Caminho esperado: {template_path.absolute()}"
            )
    
    # Valida arquivo de logs (mas não é crítico, pode ser gerado)
    if not LOGS_CSV_PATH.exists():
        errors.append(
            f"⚠️  Arquivo de logs não encontrado: {LOGS_CSV_PATH}\n"
            f"   Será gerado automaticamente se possível.\n"
            f"   Caminho esperado: {LOGS_CSV_PATH.absolute()}"
        )
    
    # Valida diretório data (para garantir que pode escrever)
    data_dir = LOGS_CSV_PATH.parent
    if not data_dir.exists():
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            errors.append(
                f"❌ Não foi possível criar diretório de dados: {data_dir}\n"
                f"   Erro: {e}"
            )
    
    # Conta apenas erros críticos (não avisos)
    critical_errors = [e for e in errors if e.startswith("❌")]
    return len(critical_errors) == 0, errors


def process_logs() -> None:
    """
    Lê os logs do CSV, aplica a lógica de roteamento e imprime um relatório
    de FinOps mostrando custo real vs. custo hipotético com apenas modelo Pro.
    
    Raises
    ------
    FileNotFoundError
        Se o arquivo de logs não existir.
    ValueError
        Se o CSV estiver vazio ou malformado.
    """
    try:
        config = load_config()
    except (FileNotFoundError, yaml.YAMLError, ValueError) as e:
        console.print(f"[bold red]Erro ao carregar configuração:[/bold red] {e}")
        sys.exit(1)
    
    try:
        env = build_prompt_env()
    except FileNotFoundError as e:
        console.print(f"[bold red]Erro ao carregar ambiente de prompts:[/bold red] {e}")
        sys.exit(1)
    
    try:
        template = env.get_template(PROMPT_TEMPLATE_NAME)
    except TemplateNotFound as e:
        console.print(
            f"[bold red]Template não encontrado:[/bold red] {PROMPT_TEMPLATE_NAME}\n"
            f"Verifique se o arquivo existe em: {PROMPTS_DIR / PROMPT_TEMPLATE_NAME}"
        )
        sys.exit(1)
    
    if not LOGS_CSV_PATH.exists():
        console.print(
            f"[bold yellow]Arquivo de logs não encontrado:[/bold yellow] {LOGS_CSV_PATH}\n"
            "[bold]Gerando arquivo de logs automaticamente...[/bold]"
        )
        try:
            generate_logs()
            console.print(f"[green]✓[/green] Arquivo gerado com sucesso!")
        except Exception as e:
            console.print(f"[bold red]Erro ao gerar logs:[/bold red] {e}")
            sys.exit(1)
    
    try:
        df = pd.read_csv(LOGS_CSV_PATH)
    except FileNotFoundError:
        console.print(f"[bold red]Arquivo não encontrado:[/bold red] {LOGS_CSV_PATH}")
        sys.exit(1)
    except pd.errors.EmptyDataError:
        console.print(f"[bold red]Arquivo CSV vazio:[/bold red] {LOGS_CSV_PATH}")
        sys.exit(1)
    except pd.errors.ParserError as e:
        console.print(f"[bold red]Erro ao ler CSV:[/bold red] {e}")
        sys.exit(1)
    
    if df.empty:
        console.print("[bold red]Arquivo CSV não contém dados.[/bold red]")
        sys.exit(1)
    
    # Validação de colunas necessárias
    required_columns = ["id", "log_message"]
    missing_columns = [col for col in required_columns if col not in df.columns]
    if missing_columns:
        console.print(
            f"[bold red]Colunas faltando no CSV:[/bold red] {missing_columns}\n"
            f"Colunas disponíveis: {list(df.columns)}"
        )
        sys.exit(1)

    table = Table(
        title="Adaptive Batch Processor - Log Analysis",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
    )
    table.add_column("Log ID", justify="right", style="cyan", no_wrap=True)
    table.add_column("Length", justify="right", style="magenta")
    table.add_column("Selected Model", style="yellow")
    table.add_column("Cost ($)", justify="right", style="green")

    total_real_cost = 0.0
    total_all_pro_cost = 0.0

    with Live(table, console=console, refresh_per_second=10) as live:
        for idx, row in df.iterrows():
            try:
                log_id = int(row["id"])
                log_message: str = str(row["log_message"])

                # 1) Seleciona o worker com base no tamanho do log
                try:
                    worker_name, worker_cfg = select_worker_for_log(log_message, config)
                    model_name = worker_cfg["model"]
                except ValueError as e:
                    console.print(
                        f"[bold red]Erro ao selecionar worker para log {log_id}:[/bold red] {e}"
                    )
                    continue

                # 2) Constrói o prompt usando o template Jinja2
                try:
                    prompt = template.render(log_message=log_message)
                except Exception as e:
                    console.print(
                        f"[bold red]Erro ao renderizar template para log {log_id}:[/bold red] {e}"
                    )
                    continue

                # 3) Estima o custo para o modelo selecionado
                try:
                    cost_real = estimate_cost(worker_cfg, prompt)
                    total_real_cost += cost_real
                except Exception as e:
                    console.print(
                        f"[bold yellow]Aviso ao calcular custo para log {log_id}:[/bold yellow] {e}"
                    )
                    cost_real = 0.0

                # 4) Estima o custo hipotético se usássemos sempre o modelo Pro
                try:
                    senior_cfg = config["workers"]["senior_engineer"]
                    cost_all_pro = estimate_cost(senior_cfg, prompt)
                    total_all_pro_cost += cost_all_pro
                except Exception as e:
                    console.print(
                        f"[bold yellow]Aviso ao calcular custo Pro para log {log_id}:[/bold yellow] {e}"
                    )
                    cost_all_pro = cost_real  # Fallback

                # 5) Mock de execução no "Vertex AI"
                try:
                    client = build_mock_client(model_name)
                    _ = client.generate(prompt)
                except Exception as e:
                    console.print(
                        f"[bold yellow]Aviso ao processar log {log_id} com {model_name}:[/bold yellow] {e}"
                    )

                # 6) Atualiza tabela Rich
                log_len = len(log_message)
                table.add_row(
                    str(log_id),
                    str(log_len),
                    worker_name,
                    f"{cost_real:.6f}",
                )
                live.update(table)
            except Exception as e:
                console.print(
                    f"[bold red]Erro inesperado ao processar linha {idx}:[/bold red] {e}"
                )
                continue

    # Cálculo de economia
    savings = max(0.0, total_all_pro_cost - total_real_cost)
    savings_pct = (savings / total_all_pro_cost * 100.0) if total_all_pro_cost > 0 else 0.0

    real_text = Text(f"Custo Total Real:     ${total_real_cost:.6f}", style="bold")
    pro_text = Text(f"Custo se apenas PRO:  ${total_all_pro_cost:.6f}", style="bold")
    savings_text = Text(
        f"Saving (economia):     ${savings:.6f}  ({savings_pct:.2f}%)",
        style="bold green",
    )

    console.print()
    console.print(
        Panel(
            Text.assemble(real_text, "\n", pro_text, "\n", savings_text),
            title="FinOps Report",
            border_style="green",
        )
    )


def main() -> None:
    """
    Função principal que pode ser chamada diretamente ou via wrapper.
    
    Executa a validação de arquivos, geração de logs e processamento.
    """
    # 1) Validação de arquivos antes de processar
    console.print("[bold cyan]Validando arquivos necessários...[/bold cyan]")
    is_valid, validation_messages = validate_files()
    
    if validation_messages:
        console.print()
        for msg in validation_messages:
            if msg.startswith("❌"):
                console.print(f"[bold red]{msg}[/bold red]")
            else:
                console.print(f"[yellow]{msg}[/yellow]")
        console.print()
    
    if not is_valid:
        console.print(
            "[bold red]Erro: Arquivos críticos não encontrados. "
            "Por favor, verifique a estrutura do projeto.[/bold red]"
        )
        sys.exit(1)
    
    # 2) Gera dados sintéticos de logs (se necessário)
    if not LOGS_CSV_PATH.exists():
        console.print("[bold yellow]Arquivo de logs não encontrado. Gerando automaticamente...[/bold yellow]")
        try:
            generated_path = generate_logs()
            console.print(f"[green]✓[/green] Arquivo de logs gerado em: {generated_path}")
        except (OSError, ValueError) as e:
            console.print(f"[bold red]Erro ao gerar logs:[/bold red] {e}")
            sys.exit(1)
    else:
        console.print(f"[green]✓[/green] Arquivo de logs encontrado: {LOGS_CSV_PATH}")

    # 3) Processa os logs com o agente adaptativo
    try:
        process_logs()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Processamento interrompido pelo usuário.[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]Erro inesperado durante o processamento:[/bold red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.print(f"[bold red]Erro fatal:[/bold red] {e}")
        sys.exit(1)

