"""
Exceções Customizadas - Governance Gateway
Define exceções específicas para melhor tratamento de erros
"""


class GovernanceGatewayError(Exception):
    """Exceção base para todos os erros do Governance Gateway."""
    pass


class PolicyValidationError(GovernanceGatewayError):
    """Erro ao validar política YAML."""
    pass


class PolicyNotFoundError(GovernanceGatewayError, FileNotFoundError):
    """Arquivo de política não encontrado."""
    pass


class TemplateNotFoundError(GovernanceGatewayError, FileNotFoundError):
    """Template Jinja2 não encontrado."""
    pass


class ModelNotFoundError(GovernanceGatewayError, KeyError):
    """Modelo não encontrado na política de preços."""
    pass


class DepartmentNotFoundError(GovernanceGatewayError, KeyError):
    """Departamento não encontrado na política."""
    pass


class InvalidComplexityError(GovernanceGatewayError, ValueError):
    """Score de complexidade inválido."""
    pass


# ============================================================================
# Exceções do Intent Guardrail (Aula 03)
# ============================================================================

class IntentBlockedError(GovernanceGatewayError):
    """Requisição bloqueada pelo Intent Guardrail."""
    
    def __init__(self, message: str, detected_risks: list[str] = None):
        """
        Inicializa exceção de bloqueio de intenção.
        
        Args:
            message: Mensagem descrevendo o bloqueio
            detected_risks: Lista de riscos detectados que causaram o bloqueio
        """
        self.detected_risks = detected_risks or []
        super().__init__(message)


class SafetyBlockedError(GovernanceGatewayError):
    """Resposta bloqueada por Safety Settings do Vertex AI."""
    pass

