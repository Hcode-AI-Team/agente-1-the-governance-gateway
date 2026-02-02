from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Dict

import pandas as pd
from rich.console import Console

console = Console()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_CSV_PATH = DATA_DIR / "logs.csv"


def _build_short_logs() -> List[str]:
    """Cria uma lista de mensagens de erro curtas para testar o modelo Flash."""
    return [
        "Connection timeout at port 80",
        "NullPointer in user_id",
        "Failed to open database connection",
        "Unauthorized access attempt detected",
        "Disk space low on /var",
        "Cache miss for user session",
        "Invalid JWT token format",
        "Email sending failed: SMTP 550",
        "Rate limit exceeded for IP 10.0.0.1",
        "Configuration file not found",
        "Permission denied while reading /etc/passwd",
        "Service unavailable: HTTP 503",
        "Could not parse JSON payload",
        "User session expired unexpectedly",
        "Deadlock detected in transaction manager",
    ]


def _build_long_stack_trace(seed: int = 0) -> str:
    """
    Gera um "stack trace" artificial longo (> 500 caracteres).

    A ideia é simular um log complexo que, em um cenário real,
    provavelmente exigiria um modelo mais caro/robusto (Pro).
    """
    base_header = (
        "Exception in thread \"main\" java.lang.NullPointerException: "
        "Cannot invoke \"com.example.Service.process(Object)\" because \"service\" is null\n"
        "\tat com.example.app.Main.processRequest(Main.java:42)\n"
        "\tat com.example.app.Main.main(Main.java:18)\n"
    )
    repeated_frame = (
        f"\tat com.example.lib.Worker.run(Worker.java:{100 + seed})\n"
        f"\tat java.base/java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:{200 + seed})\n"
        f"\tat java.base/java.lang.Thread.run(Thread.java:{300 + seed})\n"
    )

    long_body = base_header + repeated_frame * 10

    # Garante um tamanho grande o suficiente
    if len(long_body) < 600:
        long_body = long_body + (" [memory-dump-hex]" * 40)

    return long_body


def generate_logs(csv_path: Path | None = None) -> Path:
    """
    Gera um arquivo CSV com 20 linhas de logs:
    - 15 linhas de erros curtos
    - 5 linhas de stack traces longos

    Colunas:
    - id: identificador incremental do log
    - log_message: conteúdo do log
    
    Raises
    ------
    OSError
        Se não conseguir criar o diretório ou escrever o arquivo.
    ValueError
        Se os dados gerados estiverem inválidos.
    """
    target_path = csv_path or LOGS_CSV_PATH

    try:
        os.makedirs(target_path.parent, exist_ok=True)
    except OSError as e:
        raise OSError(
            f"Não foi possível criar o diretório {target_path.parent}: {e}"
        ) from e

    try:
        short_logs = _build_short_logs()
        long_logs = [_build_long_stack_trace(seed=i) for i in range(5)]
    except Exception as e:
        raise ValueError(f"Erro ao gerar dados de logs: {e}") from e

    if not short_logs or not long_logs:
        raise ValueError("Falha ao gerar logs: listas vazias")

    messages: List[str] = short_logs + long_logs

    if len(messages) != 20:
        raise ValueError(
            f"Quantidade incorreta de logs gerados: {len(messages)} (esperado: 20)"
        )

    rows: List[Dict[str, str]] = [
        {"id": idx + 1, "log_message": msg} for idx, msg in enumerate(messages)
    ]

    try:
        df = pd.DataFrame(rows, columns=["id", "log_message"])
        df.to_csv(target_path, index=False, encoding="utf-8")
    except OSError as e:
        raise OSError(
            f"Não foi possível escrever o arquivo CSV em {target_path}: {e}"
        ) from e
    except Exception as e:
        raise ValueError(f"Erro ao criar DataFrame ou salvar CSV: {e}") from e

    # Validação: verifica se o arquivo foi criado corretamente
    if not target_path.exists():
        raise OSError(f"Arquivo não foi criado: {target_path}")

    return target_path


if __name__ == "__main__":
    try:
        path = generate_logs()
        console.print(f"[green]✓[/green] Arquivo de logs gerado em: {path}")
    except (OSError, ValueError) as e:
        console.print(f"[bold red]Erro ao gerar logs:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Erro inesperado:[/bold red] {e}")
        sys.exit(1)

