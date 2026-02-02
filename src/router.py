"""
Módulo de Roteamento de Modelos - Aula 01
Implementa a lógica de decisão baseada em Tier e Complexidade

Este módulo implementa o padrão Router-Gateway, onde a escolha do modelo LLM
é desacoplada do código de negócio e gerenciada via configuração YAML.

🎯 Objetivo da Aula 01:
Demonstrar como o padrão Router-Gateway permite otimização de custos (FinOps)
sem alterar código de produção. A política em YAML define as regras, o router
apenas as executa.

Arquitetura:
- Router: Decide qual modelo usar baseado em política configurável
- Gateway: Abstrai a chamada ao modelo (será implementado na Aula 03)
- Policy: Configuração YAML que define regras de roteamento

Benefícios do padrão Router-Gateway:
- FinOps: Otimização de custos sem alterar código
- Flexibilidade: Mudanças de política não requerem deploy
- Testabilidade: Fácil testar diferentes cenários de roteamento
- Auditoria: Mudanças em políticas são rastreáveis no Git

📚 Conexão com próximas aulas:
- Aula 02: O router consultará também políticas de segurança (Intent Guardrail)
- Aula 03: O Gateway será implementado com chamadas reais ao Vertex AI
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import ValidationError

from .models import ModelPolicy, DepartmentConfig
from .exceptions import (
    PolicyValidationError,
    PolicyNotFoundError,
    DepartmentNotFoundError,
    InvalidComplexityError
)
from .logger import get_logger

logger = get_logger(__name__)


class ModelRouter:
    """
    Roteador de modelos LLM baseado em política configurável.
    
    🎯 Padrão Router-Gateway - Aula 01:
    Implementa a decisão de qual modelo usar sem conhecer detalhes de
    implementação. O router consulta a política YAML e aplica as regras
    de negócio (tier, complexidade) para escolher entre Flash e Pro.
    
    Arquitetura: O router é "stateless" - todas as regras vêm do YAML.
    Isso permite que equipes de FinOps ajustem políticas sem envolver
    desenvolvedores ou fazer deploy de código.
    
    📊 Lógica de Roteamento (Aula 01):
    - Tier 'platinum': Sempre Pro (máxima qualidade, maior custo)
    - Tier 'standard': Decisão dinâmica por complexidade (equilíbrio)
    - Tier 'budget': Sempre Flash (menor custo, boa qualidade)
    
    📚 Conexão Aula 02:
    Na próxima aula, o router também consultará políticas de segurança
    para validar a intenção do usuário antes de rotear para um modelo.
    """
    
    def __init__(self, policy_path: str = "config/model_policy.yaml"):
        """
        Inicializa o roteador carregando a política do YAML.
        
        🏗️ Estrutura ADK - Aula 01:
        A política está em config/ seguindo o padrão ADK:
        - config/model_policy.yaml: Define tiers e thresholds
        - prompts/: Templates de prompts (usado pelo Gateway)
        - tools/: Ferramentas do agente (aulas futuras)
        
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
        
        🏗️ Validação Pydantic - Aula 01:
        Pydantic garante que a política YAML está correta antes de usar.
        Erros de configuração são detectados na inicialização, não em produção.
        
        📚 Conexão Aula 03:
        A mesma validação Pydantic será usada para validar respostas JSON
        do LLM, garantindo que o modelo retornou dados no formato esperado.
        
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
        
        🎯 Aula 01 - FinOps em Ação:
        Esta é a função central do router. Ela aplica a política de negócio
        para escolher entre modelos caros (Pro) e econômicos (Flash), otimizando
        custos sem sacrificar qualidade onde ela importa.
        
        Lógica de decisão por tier:
        - Tier 'platinum': Sempre usa Gemini Pro (ignora complexidade)
          Exemplo: Departamento Jurídico - precisão máxima é crítica
          
        - Tier 'standard': Usa Flash se complexidade < threshold, senão Pro
          Exemplo: RH - operações simples usam Flash, complexas usam Pro
          
        - Tier 'budget': Sempre usa Gemini Flash (ignora complexidade)
          Exemplo: TI Ops - operações rotineiras não justificam modelo premium
        
        📊 Impacto Financeiro:
        A escolha correta pode resultar em 16x de economia:
        - Pro: ~$1.25/1M input tokens
        - Flash: ~$0.075/1M input tokens
        
        📚 Conexão Aula 02:
        Na próxima aula, adicionaremos uma validação ANTES do roteamento:
        Intent Guardrail verificará se a requisição é segura/pertinente
        antes de decidir qual modelo usar.
        
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
        fixed_model = dept_config.model  # Modelo fixo (se configurado)
        threshold = dept_config.complexity_threshold
        
        # ------------------------------------------------------------------------
        # Lógica de Roteamento por Tier - Aula 01
        # ------------------------------------------------------------------------
        
        # Tier Platinum: Sempre usa Pro (máxima qualidade)
        # Caso de uso: Departamento Jurídico
        # Justificativa: Requisitos legais exigem precisão máxima, custo é secundário
        if tier == 'platinum':
            model = 'gemini-1.5-pro-001'
            logger.info(f"Tier platinum selecionado: {model}")
            return model
        
        # Tier Budget: Sempre usa Flash (otimização de custos)
        # Caso de uso: Operações de TI
        # Justificativa: Operações rotineiras não requerem modelo premium
        if tier == 'budget':
            model = 'gemini-1.5-flash-001'
            logger.info(f"Tier budget selecionado: {model}")
            return model
        
        # Tier Standard: Decisão dinâmica baseada em complexidade
        # Caso de uso: Recursos Humanos
        # Justificativa: Balanceamento entre custo e qualidade
        # - Operações simples (< threshold): Flash economiza sem perder qualidade
        # - Operações complexas (>= threshold): Pro garante precisão quando necessário
        if tier == 'standard':
            # Validação: Tier standard requer threshold definido
            if threshold is None:
                logger.error(f"Tier standard sem threshold: {department}")
                raise PolicyValidationError(
                    f"Departamento '{department}' (tier standard) requer complexity_threshold"
                )
            
            # Decisão baseada em complexidade vs threshold
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
