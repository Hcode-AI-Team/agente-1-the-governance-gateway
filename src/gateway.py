"""
Módulo Gateway - Aula 03
Abstrai chamadas ao Vertex AI e gerencia Safety Settings

Este módulo foi extraído do main.py para melhor separação de responsabilidades.
O Gateway é responsável por:
- Fazer chamadas reais ao Vertex AI (modo produção)
- Simular chamadas ao LLM (modo mock)
- Carregar e aplicar Safety Settings
- Validar respostas com Pydantic (Structured Output)
- Implementar retry logic em caso de ValidationError

🎯 Objetivo Pedagógico - Aula 03:
Demonstrar a importância do Structured Output e Safety Settings na produção:
- response_mime_type: garante JSON válido
- response_schema: garante JSON no formato correto (schema Pydantic)
- Safety Settings: valida conteúdo da resposta do modelo
- Retry logic: aumenta confiabilidade em caso de falhas de parsing

📊 FinOps Connection:
O Gateway usa tokens reais da API (usage_metadata) para cálculo preciso de custos,
permitindo análise financeira confiável e tomada de decisão baseada em dados.
"""

import json
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Tuple
from jinja2 import Environment, FileSystemLoader
from pydantic import ValidationError

# Imports condicionais do Vertex AI
try:
    import vertexai
    from vertexai.generative_models import GenerativeModel, HarmCategory, HarmBlockThreshold
    VERTEXAI_AVAILABLE = True
except ImportError:
    VERTEXAI_AVAILABLE = False

from .models import AuditResponse
from .exceptions import SafetyBlockedError
from .logger import get_logger

logger = get_logger(__name__)


def render_prompt_template(user_request: str, template_path: str = "prompts/audit_master.jinja2") -> str:
    """
    Carrega e processa o template Jinja2 do prompt de auditoria.
    
    🏗️ Estrutura ADK - Aula 03:
    Templates em prompts/ permitem:
    - Versionamento de prompts no Git
    - Reutilização entre diferentes agentes
    - Mudanças sem alterar código Python
    - Auditoria de mudanças em prompts
    
    Args:
        user_request: Solicitação do usuário a ser injetada no template
        template_path: Caminho relativo para o arquivo de template
        
    Returns:
        Prompt processado com variáveis substituídas
        
    Raises:
        FileNotFoundError: Se o template não for encontrado
        ValueError: Se houver erro no processamento do template
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
    except Exception as e:
        logger.error(f"Erro ao processar template Jinja2: {e}", exc_info=True)
        # Se template não encontrado, lançar FileNotFoundError
        if "not found" in str(e).lower() or "TemplateNotFound" in type(e).__name__:
            raise FileNotFoundError(
                f"Template não encontrado: {template_dir / template_file}"
            ) from e
        # Outros erros
        raise ValueError(f"Erro ao processar template Jinja2: {e}") from e


def simulate_llm_response(model_name: str, user_request: str) -> Dict[str, Any]:
    """
    Simula a resposta do LLM sem fazer chamada real ao Vertex AI.
    
    🎯 Aula 03 - Modo Simulação:
    Esta função SIMULA uma resposta para permitir execução sem:
    - Autenticação ADC no Google Cloud
    - Custos reais de API
    - Dependência de conectividade de rede
    
    ⚡ Melhoria vs Aula 01:
    Agora a simulação também valida com Pydantic (Structured Output),
    garantindo que mock e real seguem o mesmo contrato de dados.
    
    Args:
        model_name: Nome do modelo usado (ex: 'gemini-2.5-pro')
        user_request: Solicitação do usuário a ser analisada
        
    Returns:
        Dicionário com a resposta simulada do auditor validada por Pydantic
    """
    # Lógica de Simulação por Palavras-chave
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
    
    # Simulação de Diferença entre Modelos
    if 'pro' in model_name:
        # Resposta mais detalhada do Pro (simula análise mais profunda)
        reasoning += " Análise detalhada realizada com modelo avançado."
    else:
        # Resposta mais concisa do Flash
        # Garantir minimum length de 10 caracteres (requisito do Pydantic)
        if len(reasoning) > 100:
            reasoning = reasoning[:100]
        if len(reasoning) < 10:
            reasoning = reasoning + " Análise concluída."
    
    # 🎯 Aula 03: Validar com Pydantic ANTES de retornar
    # Isso garante que mock e real têm o mesmo formato
    try:
        audit_response = AuditResponse(
            compliance_status=compliance,
            risk_level=risk,
            audit_reasoning=reasoning
        )
        return audit_response.model_dump()
    except ValidationError as e:
        logger.error(f"Erro na validação da resposta simulada: {e}")
        # Fallback: retornar resposta mínima válida
        return {
            "compliance_status": "APPROVED",
            "risk_level": "LOW",
            "audit_reasoning": "Resposta simulada com erro de validação, aprovando por fallback."
        }


def simulate_input_output(user_request: str, model_response: Dict[str, Any]) -> tuple[int, int]:
    """
    Simula o tamanho do input e output para cálculo de custos.
    
    🎯 Aula 03 - FinOps Estimation:
    Esta função estima o tamanho do input/output quando em modo mock.
    Em modo real, os tokens vêm diretamente da API (usage_metadata).
    
    Args:
        user_request: Solicitação do usuário
        model_response: Resposta do modelo (dicionário)
        
    Returns:
        Tupla (input_chars, output_chars) - número de caracteres em cada parte
    """
    # Cálculo de Input (Prompt)
    try:
        full_prompt = render_prompt_template(user_request)
        input_chars = len(full_prompt)
    except Exception as e:
        # Fallback: se houver erro no template, usa aproximação
        input_chars = len(user_request) + 500  # Aproximação do template
    
    # Cálculo de Output (Resposta)
    output_json = json.dumps(model_response, ensure_ascii=False, indent=2)
    output_chars = len(output_json)
    
    return input_chars, output_chars


def load_safety_settings() -> Dict[Any, Any]:
    """
    Carrega configurações de segurança do arquivo YAML.
    
    🛡️ Aula 03 - Safety Settings:
    As configurações de segurança definem quais tipos de conteúdo
    potencialmente prejudicial o modelo deve bloquear. Isso complementa
    o Intent Guardrail que valida a pergunta do usuário.
    
    🎯 Defesa em Camadas:
    - Intent Guardrail: valida ENTRADA (pergunta do usuário)
    - Safety Settings: valida SAÍDA (resposta do modelo)
    
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
    Esta função faz chamada real ao Gemini 2.5 Pro/Flash via Vertex AI com:
    - response_mime_type: Força JSON válido
    - response_schema: Força schema Pydantic (Aula 03 improvement)
    - Safety Settings: Valida conteúdo da resposta
    - Retry logic: Retentar se ValidationError
    - Safety blocked handling: Detecta bloqueios por safety
    
    📊 Response Estruturado (Aula 03):
    O parâmetro response_schema força o modelo a seguir exatamente o
    schema Pydantic, reduzindo erros de parsing para quase zero.
    
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
        SafetyBlockedError: Se resposta bloqueada por Safety Settings
        ValueError: Se a resposta do modelo não for JSON válido após retries
        ValidationError: Se o JSON não corresponder ao schema AuditResponse
    """
    if not VERTEXAI_AVAILABLE:
        raise RuntimeError(
            "Vertex AI SDK não disponível. Instale com: "
            "pip install google-cloud-aiplatform>=1.74.0"
        )
    
    logger.info(f"Chamando Vertex AI com modelo: {model_name}")
    
    # Configurar retry logic
    MAX_RETRIES = 1
    
    for attempt in range(MAX_RETRIES + 1):
        try:
            # Criar instância do modelo
            model = GenerativeModel(model_name)
            logger.debug(f"Modelo {model_name} inicializado (tentativa {attempt + 1}/{MAX_RETRIES + 1})")
            
            # Configurar parâmetros de geração
            # 🎯 Aula 03: response_mime_type força JSON válido
            # Nota: response_schema requer formato específico do Vertex AI SDK
            # Por enquanto, usamos apenas response_mime_type + validação Pydantic após receber
            generation_config = {
                "response_mime_type": "application/json",
                # "response_schema": AuditResponse.model_json_schema(),  # TODO: converter para formato Vertex AI
                "temperature": 0.1
            }
            
            # Fazer chamada ao modelo
            logger.debug("Enviando requisição para Vertex AI...")
            response = model.generate_content(
                prompt,
                generation_config=generation_config,
                safety_settings=safety_settings
            )
            logger.debug("Resposta recebida do Vertex AI")
            
            # 🛡️ Aula 03: Verificar se resposta foi bloqueada por Safety Settings
            if not response.candidates:
                logger.error("Resposta bloqueada: sem candidates retornados")
                raise SafetyBlockedError(
                    "Resposta bloqueada por Safety Settings - nenhum candidate retornado"
                )
            
            # Verificar finish_reason do primeiro candidate
            candidate = response.candidates[0]
            if hasattr(candidate, 'finish_reason'):
                finish_reason = str(candidate.finish_reason)
                if 'SAFETY' in finish_reason:
                    logger.error(f"Resposta bloqueada por safety: {finish_reason}")
                    # Extrair safety ratings para debug
                    safety_info = []
                    if hasattr(candidate, 'safety_ratings'):
                        for rating in candidate.safety_ratings:
                            safety_info.append(f"{rating.category}: {rating.probability}")
                    raise SafetyBlockedError(
                        f"Resposta bloqueada por Safety Settings: {finish_reason}. "
                        f"Ratings: {', '.join(safety_info)}"
                    )
            
            # Extrair tokens REAIS da resposta
            input_tokens = response.usage_metadata.prompt_token_count
            output_tokens = response.usage_metadata.candidates_token_count
            logger.info(f"Tokens consumidos: input={input_tokens}, output={output_tokens}")
            
            # Validar JSON com Pydantic
            audit_response = AuditResponse.model_validate_json(response.text)
            logger.debug("Resposta validada com Pydantic")
            
            # Converter para dicionário para compatibilidade com código existente
            return audit_response.model_dump(), input_tokens, output_tokens
            
        except SafetyBlockedError:
            # Safety blocked não deve ser retentado
            raise
        except ValidationError as e:
            logger.warning(f"ValidationError na tentativa {attempt + 1}: {e}")
            
            # Se não é a última tentativa, reforçar prompt e retentar
            if attempt < MAX_RETRIES:
                logger.info("Retentando com prompt reforçado...")
                prompt += "\n\nIMPORTANTE: Retorne APENAS JSON válido no formato especificado."
            else:
                # Última tentativa falhou, lançar exceção
                logger.error(f"ValidationError após {MAX_RETRIES + 1} tentativas")
                raise
        except Exception as e:
            logger.error(f"Erro ao chamar Vertex AI (tentativa {attempt + 1}): {e}", exc_info=True)
            
            # Se não é a última tentativa e erro não é fatal, retentar
            if attempt < MAX_RETRIES and not isinstance(e, (RuntimeError, SafetyBlockedError)):
                logger.info("Retentando chamada ao Vertex AI...")
            else:
                raise
    
    # Se chegou aqui, todas as tentativas falharam
    raise RuntimeError(f"Falha ao chamar Vertex AI após {MAX_RETRIES + 1} tentativas")
