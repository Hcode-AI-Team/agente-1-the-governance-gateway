"""
Módulo de Telemetria e FinOps
Responsável por calcular custos de operação baseado em uso de tokens

Este módulo implementa a calculadora de custos (FinOps) para operações
com modelos LLM. O cálculo é baseado em:
- Número de tokens de input (prompt enviado ao modelo)
- Número de tokens de output (resposta do modelo)
- Preços por modelo (definidos em model_policy.yaml)

Arquitetura:
- Desacopla cálculo de custos do código de roteamento
- Permite diferentes estratégias de pricing sem alterar código
- Facilita análise de custos e otimização (FinOps)

Uso:
    estimator = CostEstimator()
    cost = estimator.calculate_cost('gemini-1.5-pro-001', 1000, 500)
    # Retorna custo em USD com 6 casas decimais
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import ValidationError

from src.models import ModelPolicy, PricingModel
from src.exceptions import (
    PolicyValidationError,
    PolicyNotFoundError,
    ModelNotFoundError
)
from src.logger import get_logger

logger = get_logger(__name__)


class CostEstimator:
    """
    Calculadora de custos para operações com modelos LLM.
    
    Arquitetura: Desacopla o cálculo de custos do roteamento, permitindo
    que diferentes estratégias de pricing sejam aplicadas sem modificar
    o código de negócio.
    """
    
    # ------------------------------------------------------------------------
    # Constantes de Conversão
    # ------------------------------------------------------------------------
    # Assumindo 1 token ≈ 4 caracteres (aproximação comum para modelos baseados em BPE)
    # 
    # Nota: Esta é uma aproximação simplificada para demonstração.
    # Em produção, use a biblioteca tiktoken ou a API do Vertex AI
    # para contar tokens com precisão, pois a relação varia por modelo.
    CHARS_PER_TOKEN = 4
    
    def __init__(self, policy_path: str = "config/model_policy.yaml"):
        """
        Inicializa o estimador carregando a política de preços do YAML.
        
        Args:
            policy_path: Caminho para o arquivo YAML com política de preços
        """
        # Resolver caminho relativo à raiz do projeto
        project_root = Path(__file__).parent.parent
        self.policy_path = project_root / policy_path
        self.policy: Optional[ModelPolicy] = None
        self.pricing: Dict[str, PricingModel] = {}
        self._load_pricing()
    
    def _load_pricing(self) -> None:
        """
        Carrega e valida a seção de pricing do arquivo YAML de política.
        
        Este método carrega o YAML, valida com Pydantic e extrai a seção
        'pricing com preços por modelo (input/output separados).
        
        Raises:
            FileNotFoundError: Se o arquivo de política não existir
            ValueError: Se o YAML estiver malformado ou inválido
            ValidationError: Se a estrutura não corresponder ao schema Pydantic
        """
        try:
            logger.debug(f"Carregando política de preços de: {self.policy_path}")
            with open(self.policy_path, 'r', encoding='utf-8') as f:
                policy_data = yaml.safe_load(f)
            logger.debug("YAML de preços carregado com sucesso")
        except FileNotFoundError as e:
            logger.error(f"Arquivo de política não encontrado: {self.policy_path}")
            raise PolicyNotFoundError(
                f"Arquivo de política não encontrado: {self.policy_path}"
            ) from e
        except yaml.YAMLError as e:
            logger.error(f"Erro ao processar YAML: {e}")
            raise ValueError(f"Erro ao processar YAML: {e}") from e
        
        # Validação com Pydantic
        try:
            logger.debug("Validando política de preços com Pydantic")
            self.policy = ModelPolicy(**policy_data)
            self.pricing = self.policy.pricing
            logger.info(f"Política de preços validada: {len(self.pricing)} modelos configurados")
        except ValidationError as e:
            logger.error(f"Erro de validação Pydantic: {e}")
            raise PolicyValidationError(
                f"Erro ao validar política: {e}. "
                "Verifique se o YAML está no formato correto."
            ) from e
        except Exception as e:
            logger.error(f"Erro inesperado ao validar política: {e}", exc_info=True)
            raise PolicyValidationError(
                f"Erro inesperado ao validar política: {e}"
            ) from e
    
    def _chars_to_tokens(self, char_count: int) -> int:
        """
        Converte caracteres para tokens usando aproximação.
        
        Args:
            char_count: Número de caracteres
            
        Returns:
            Número estimado de tokens
        """
        return max(1, char_count // self.CHARS_PER_TOKEN)
    
    def calculate_cost(
        self, 
        model_name: str, 
        input_chars: int, 
        output_chars: int
    ) -> float:
        """
        Calcula o custo total de uma operação com o modelo.
        
        Args:
            model_name: Nome do modelo (ex: 'gemini-1.5-pro-001')
            input_chars: Número de caracteres no input
            output_chars: Número de caracteres no output
            
        Returns:
            Custo total em USD com 6 casas decimais
            
        Raises:
            KeyError: Se o modelo não estiver na política de preços
        """
        logger.debug(f"Calculando custo: model={model_name}, input={input_chars} chars, output={output_chars} chars")
        
        if model_name not in self.pricing:
            logger.warning(f"Modelo não encontrado na política: {model_name}")
            raise ModelNotFoundError(
                f"Modelo '{model_name}' não encontrado na política de preços"
            )
        
        # Obtém preços do modelo da política validada
        model_pricing = self.pricing[model_name]
        
        # ------------------------------------------------------------------------
        # Conversão e Cálculo de Custos
        # ------------------------------------------------------------------------
        # Passo 1: Converter caracteres para tokens (aproximação)
        input_tokens = self._chars_to_tokens(input_chars)
        output_tokens = self._chars_to_tokens(output_chars)
        logger.debug(f"Tokens estimados: input={input_tokens}, output={output_tokens}")
        
        # Passo 2: Calcular custos (preços no YAML são por 1k tokens)
        # Exemplo: 500 tokens = 0.5 * preço_por_1k
        # Usa os atributos do modelo Pydantic validado
        input_cost = (input_tokens / 1000.0) * model_pricing.input_per_1k_tokens
        output_cost = (output_tokens / 1000.0) * model_pricing.output_per_1k_tokens
        
        # Passo 3: Custo total = input + output
        total_cost = input_cost + output_cost
        
        # Passo 4: Retornar com 6 casas decimais (precisão para microtransações)
        cost_rounded = round(total_cost, 6)
        logger.info(f"Custo calculado: ${cost_rounded:.6f} USD para {model_name}")
        return cost_rounded

