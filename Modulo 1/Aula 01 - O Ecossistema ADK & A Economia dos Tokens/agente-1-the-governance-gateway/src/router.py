"""
Módulo de Roteamento de Modelos
Implementa a lógica de decisão baseada em Tier e Complexidade

Este módulo implementa o padrão Router-Gateway, onde a escolha do modelo LLM
é desacoplada do código de negócio e gerenciada via configuração YAML.

Arquitetura:
- Router: Decide qual modelo usar baseado em política configurável
- Gateway: Abstrai a chamada ao modelo (não implementado nesta demo)
- Policy: Configuração YAML que define regras de roteamento

Benefícios:
- FinOps: Otimização de custos sem alterar código
- Flexibilidade: Mudanças de política não requerem deploy
- Testabilidade: Fácil testar diferentes cenários de roteamento
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import ValidationError

from src.models import ModelPolicy, DepartmentConfig
from src.exceptions import (
    PolicyValidationError,
    PolicyNotFoundError,
    DepartmentNotFoundError,
    InvalidComplexityError
)
from src.logger import get_logger

logger = get_logger(__name__)


class ModelRouter:
    """
    Roteador de modelos LLM baseado em política configurável.
    
    Arquitetura: Implementa o padrão Router-Gateway, onde a escolha do modelo
    é desacoplada do código e gerenciada via configuração YAML. Isso permite
    otimização de custos (FinOps) sem modificar código de produção.
    """
    
    def __init__(self, policy_path: str = "config/model_policy.yaml"):
        """
        Inicializa o roteador carregando a política do YAML.
        
        Args:
            policy_path: Caminho para o arquivo YAML com política de roteamento
        """
        # Resolver caminho relativo à raiz do projeto
        project_root = Path(__file__).parent.parent
        self.policy_path = project_root / policy_path
        self.policy: Optional[ModelPolicy] = None
        self.departments: Dict[str, DepartmentConfig] = {}
        self._load_policy()
    
    def _load_policy(self) -> None:
        """
        Carrega e valida a política de roteamento do arquivo YAML.
        
        Este método carrega o YAML, valida com Pydantic e armazena
        a política validada na memória.
        
        Raises:
            FileNotFoundError: Se o arquivo de política não existir
            ValueError: Se o YAML estiver malformado ou inválido
            ValidationError: Se a estrutura não corresponder ao schema Pydantic
        """
        try:
            logger.debug(f"Carregando política de: {self.policy_path}")
            with open(self.policy_path, 'r', encoding='utf-8') as f:
                policy_data = yaml.safe_load(f)
            logger.debug("YAML carregado com sucesso")
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
            logger.debug("Validando política com Pydantic")
            self.policy = ModelPolicy(**policy_data)
            self.departments = self.policy.departments
            logger.info(f"Política validada: {len(self.departments)} departamentos configurados")
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
    
    def route_request(self, department: str, complexity_score: float) -> str:
        """
        Determina qual modelo usar baseado no departamento e complexidade.
        
        Lógica de decisão:
        - Tier 'platinum': Sempre usa Gemini Pro (ignora complexidade)
        - Tier 'standard': Usa Flash se complexidade < threshold, senão Pro
        - Tier 'budget': Sempre usa Gemini Flash (ignora complexidade)
        
        Args:
            department: Nome do departamento (ex: 'legal_dept')
            complexity_score: Score de complexidade (0.0 a 1.0)
            
        Returns:
            Nome do modelo a ser usado (ex: 'gemini-1.5-pro-001')
            
        Raises:
            KeyError: Se o departamento não estiver na política
            ValueError: Se complexity_score estiver fora do range válido
        """
        logger.debug(f"Roteando requisição: dept={department}, complexity={complexity_score}")
        
        if department not in self.departments:
            logger.warning(f"Departamento não encontrado: {department}")
            raise DepartmentNotFoundError(
                f"Departamento '{department}' não encontrado na política"
            )
        
        if not 0.0 <= complexity_score <= 1.0:
            logger.warning(f"Complexity score inválido: {complexity_score}")
            raise InvalidComplexityError(
                f"complexity_score deve estar entre 0.0 e 1.0, recebido: {complexity_score}"
            )
        
        # Extrai configuração do departamento da política validada
        dept_config = self.departments[department]
        tier = dept_config.tier
        fixed_model = dept_config.model  # Não usado atualmente, mas disponível
        threshold = dept_config.complexity_threshold
        
        # ------------------------------------------------------------------------
        # Lógica de Roteamento por Tier
        # ------------------------------------------------------------------------
        
        # Tier Platinum: Sempre usa Pro (máxima qualidade)
        # Exemplo: legal_dept - Requisitos legais exigem precisão máxima
        if tier == 'platinum':
            model = 'gemini-1.5-pro-001'
            logger.info(f"Tier platinum selecionado: {model}")
            return model
        
        # Tier Budget: Sempre usa Flash (otimização de custos)
        # Exemplo: it_ops - Operações rotineiras não requerem modelo premium
        if tier == 'budget':
            model = 'gemini-1.5-flash-001'
            logger.info(f"Tier budget selecionado: {model}")
            return model
        
        # Tier Standard: Decisão dinâmica baseada em complexidade
        # Exemplo: hr_dept - Balanceamento entre custo e qualidade
        if tier == 'standard':
            # Validação: Tier standard requer threshold definido
            if threshold is None:
                logger.error(f"Tier standard sem threshold: {department}")
                raise PolicyValidationError(
                    f"Departamento '{department}' (tier standard) requer complexity_threshold"
                )
            
            # Se complexidade baixa (< threshold): usa Flash (econômico)
            # Se complexidade alta (>= threshold): usa Pro (precisão)
            if complexity_score < threshold:
                model = 'gemini-1.5-flash-001'
                logger.info(f"Tier standard (complexidade baixa): {model}")
            else:
                model = 'gemini-1.5-pro-001'
                logger.info(f"Tier standard (complexidade alta): {model}")
            return model
        
        # Fallback: Tier não mapeado (erro de configuração)
        logger.error(f"Tier não suportado: {tier} para {department}")
        raise PolicyValidationError(
            f"Tier '{tier}' não suportado para departamento '{department}'"
        )

