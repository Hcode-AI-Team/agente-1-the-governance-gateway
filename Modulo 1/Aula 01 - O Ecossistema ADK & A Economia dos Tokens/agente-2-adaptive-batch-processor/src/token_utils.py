from __future__ import annotations

from typing import Mapping, Any


def estimate_cost(model_config: Mapping[str, Any], text_content: str) -> float:
    """
    Estima o custo de processamento de um texto com base na configuração do modelo.

    Heurística simples:
    - 1 token ~= 4 caracteres
    - custo = (tokens / 1000) * price_per_1k_input

    Parâmetros
    ----------
    model_config:
        Dicionário com pelo menos a chave "price_per_1k_input".
    text_content:
        Conteúdo textual de entrada.

    Returns
    -------
    float
        Custo estimado em dólares.

    Raises
    ------
    ValueError
        Se model_config não contiver "price_per_1k_input" ou se o preço for negativo.
    TypeError
        Se text_content não for uma string.
    """
    if text_content is None:
        text_content = ""
    
    if not isinstance(text_content, str):
        raise TypeError(
            f"text_content deve ser uma string, recebido: {type(text_content).__name__}"
        )

    if not model_config:
        raise ValueError("model_config não pode estar vazio")

    price_per_1k = model_config.get("price_per_1k_input")
    if price_per_1k is None:
        raise ValueError(
            "model_config deve conter a chave 'price_per_1k_input'"
        )
    
    try:
        price_per_1k = float(price_per_1k)
    except (ValueError, TypeError) as e:
        raise ValueError(
            f"price_per_1k_input deve ser um número válido, recebido: {price_per_1k}"
        ) from e
    
    if price_per_1k < 0:
        raise ValueError(
            f"price_per_1k_input não pode ser negativo, recebido: {price_per_1k}"
        )

    chars = len(text_content)
    # Garante pelo menos 1 token para não retornar custo 0 em textos muito curtos
    tokens = max(1.0, chars / 4.0)

    cost = (tokens / 1000.0) * price_per_1k

    # Garante que o custo nunca seja negativo
    return max(0.0, cost)

