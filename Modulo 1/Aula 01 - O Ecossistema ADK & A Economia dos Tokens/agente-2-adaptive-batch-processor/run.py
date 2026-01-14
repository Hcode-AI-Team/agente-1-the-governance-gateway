#!/usr/bin/env python3
"""
Script wrapper para executar o Adaptive Batch Processor diretamente.

Este script pode ser executado de duas formas:
    python run.py
    ou
    python -m src.processor

Ambos funcionam da mesma forma.
"""

import sys
from pathlib import Path

# Adiciona o diretório raiz ao path para permitir imports absolutos
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Importa e executa o processador principal
if __name__ == "__main__":
    try:
        from src.processor import main
    except ImportError as e:
        from rich.console import Console
        console = Console()
        console.print(
            f"[bold red]Erro ao importar módulos:[/bold red] {e}\n"
            "[yellow]Certifique-se de que todas as dependências estão instaladas:[/yellow]\n"
            "[cyan]pip install -r requirements.txt[/cyan]"
        )
        sys.exit(1)
    
    try:
        main()
    except KeyboardInterrupt:
        from rich.console import Console
        console = Console()
        console.print("\n[bold yellow]Processamento interrompido pelo usuário.[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        from rich.console import Console
        console = Console()
        console.print(f"[bold red]Erro fatal:[/bold red] {e}")
        sys.exit(1)
