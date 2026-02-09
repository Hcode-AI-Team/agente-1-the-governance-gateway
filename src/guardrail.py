"""
Módulo Intent Guardrail - Aula 03
Valida a intenção do usuário ANTES de processar com o LLM principal

Este módulo implementa defesa em camadas (defense in depth) para proteger
o agente de auditoria bancária contra:
- Prompt injection (tentativas de modificar comportamento)
- Prompt extraction (tentativas de extrair regras internas)
- Engenharia social (fingir autoridade)
- Requisições fora de escopo

🎯 Objetivo Pedagógico:
Demonstrar que segurança não é um custo, é um investimento. O Guardrail:
1. Protege o agente (segurança)
2. Economiza tokens (FinOps)
3. Melhora a experiência do usuário (feedback imediato em caso de bloqueio)

🏗️ Arquitetura de Duas Camadas:
- Camada 1 (Pattern Matching): Regex compilado, custo zero, detecta ameaças óbvias
- Camada 2 (LLM Classification): Gemini Flash, custo baixo, análise semântica profunda

📊 FinOps Connection:
Se 10% das requisições são bloqueadas pelo guardrail, economizamos 10% dos
custos do modelo principal (Pro). O custo do Flash é ~20x menor que Pro,
então o ROI é positivo a partir de 5% de bloqueios.
"""

import re
import os
import yaml
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Pattern
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from pydantic import ValidationError

# Imports condicionais do Google GenAI SDK (substitui vertexai.generative_models)
try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

from .models import IntentClassification, GuardrailResult
from .exceptions import IntentBlockedError, PolicyNotFoundError
from .logger import get_logger

logger = get_logger(__name__)


class IntentGuardrail:
    """
    Intent Guardrail com defesa em duas camadas.
    
    🎯 Aula 03 - Defensive Engineering:
    Implementa os seguintes Defensive Engineering Goals:
    - Input validation (Prompt Injection Protection)
    - System prompt protection (Privacy Enhancements)
    - Data minimization (Privacy Enhancements)
    - Audit logging (Privacy Enhancements)
    
    Arquitetura:
    - Camada 1: Pattern Matching via regex (custo zero)
    - Camada 2: LLM Classification via Flash (custo baixo)
    
    Fluxo de Decisão:
    1. Camada 1 detecta ameaça? → BLOCKED (economiza tokens)
    2. Camada 1 não detecta? → Camada 2 analisa semanticamente
    3. Camada 2 não detecta? → ALLOWED (prossegue ao router)
    """
    
    def __init__(self, config_path: str = "config/intent_guardrail.yaml", client=None):
        """
        Inicializa o Intent Guardrail carregando configurações e compilando regex.
        
        🏗️ Estrutura ADK:
        A configuração está em config/ seguindo o padrão ADK, permitindo
        que equipes de segurança atualizem padrões sem alterar código Python.
        
        Args:
            config_path: Caminho para o arquivo YAML com configurações do guardrail
            client: Instância do genai.Client (opcional, necessário para Camada 2 em modo real)
            
        Raises:
            PolicyNotFoundError: Se o arquivo de configuração não existir
            ValueError: Se o YAML estiver malformado
        """
        # Resolver caminho relativo à raiz do projeto
        project_root = Path(__file__).parent.parent
        self.config_path = project_root / config_path
        self.config: Dict[str, Any] = {}
        self.compiled_patterns: Dict[str, list[Pattern]] = {}
        self.client = client  # Google GenAI client para Camada 2
        
        # Carregar configurações
        self._load_config()
        
        # Compilar padrões de regex (performance)
        self._compile_patterns()
        
        # Configurar template Jinja2 para Camada 2
        self._setup_template_engine()
        
        logger.info("Intent Guardrail inicializado com sucesso")
    
    def _load_config(self) -> None:
        """
        Carrega configurações do YAML.
        
        Raises:
            PolicyNotFoundError: Se arquivo não existir
            ValueError: Se YAML malformado
        """
        try:
            logger.debug(f"Carregando configuração de: {self.config_path}")
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)
            logger.debug("Configuração carregada com sucesso")
        except FileNotFoundError as e:
            logger.error(f"Arquivo de configuração não encontrado: {self.config_path}")
            raise PolicyNotFoundError(
                f"Arquivo de configuração do guardrail não encontrado: {self.config_path}"
            ) from e
        except yaml.YAMLError as e:
            logger.error(f"Erro ao processar YAML: {e}")
            raise ValueError(f"Erro ao processar YAML: {e}") from e
    
    def _compile_patterns(self) -> None:
        """
        Compila padrões de regex para melhor performance.
        
        🎯 Aula 03 - Performance:
        Compilar regex uma vez no __init__() é muito mais eficiente do que
        compilar a cada requisição. Para 1000 requisições/dia, isso economiza
        milhares de compilações redundantes.
        """
        threat_patterns = self.config.get('threat_patterns', {})
        
        for category, patterns in threat_patterns.items():
            compiled_list = []
            for pattern in patterns:
                try:
                    # re.IGNORECASE: "Ignore" e "ignore" detectados igualmente
                    # re.UNICODE: Suporte a caracteres acentuados (português)
                    compiled = re.compile(pattern, re.IGNORECASE | re.UNICODE)
                    compiled_list.append(compiled)
                    logger.debug(f"Padrão compilado [{category}]: {pattern}")
                except re.error as e:
                    logger.warning(f"Regex inválido [{category}]: {pattern} - {e}")
            
            self.compiled_patterns[category] = compiled_list
        
        logger.info(f"Compilados {sum(len(p) for p in self.compiled_patterns.values())} padrões de ameaça")
    
    def _setup_template_engine(self) -> None:
        """
        Configura engine Jinja2 para renderizar template da Camada 2.
        """
        project_root = Path(__file__).parent.parent
        template_dir = project_root / "prompts"
        
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True
        )
        logger.debug(f"Template engine configurado: {template_dir}")
    
    def validate_intent(self, user_request: str) -> GuardrailResult:
        """
        Valida a intenção do usuário usando as duas camadas.
        
        🎯 Aula 03 - Defesa em Camadas:
        Este é o método público principal do Guardrail. Orquestra a validação
        em duas etapas para balancear segurança e custo.
        
        Fluxo:
        1. Tenta Camada 1 (pattern matching - custo zero)
        2. Se Camada 1 não detecta ameaça, usa Camada 2 (LLM - custo baixo)
        3. Retorna resultado com informações de custo e auditoria
        
        Args:
            user_request: Requisição do usuário a ser validada
            
        Returns:
            GuardrailResult com classificação e metadados
            
        Raises:
            IntentBlockedError: Se requisição for bloqueada (opcional, dependendo do uso)
        """
        logger.info(f"Validando intenção: {self._sanitize_for_log(user_request)}")
        
        # ------------------------------------------------------------------------
        # Camada 1: Pattern Matching (Custo Zero)
        # ------------------------------------------------------------------------
        layer1_result = self._layer1_pattern_matching(user_request)
        
        if layer1_result is not None:
            # Camada 1 detectou ameaça - bloquear imediatamente
            logger.warning(
                f"Camada 1 bloqueou requisição: {layer1_result.intent_category} - "
                f"Riscos: {layer1_result.detected_risks}"
            )
            
            # Calcular custo evitado (não precisou chamar LLM principal)
            cost_avoided = self._estimate_cost_avoided(user_request)
            
            return GuardrailResult(
                layer="pattern_matching",
                classification=layer1_result,
                tokens_used=0,  # Pattern matching não usa tokens
                cost_avoided=cost_avoided
            )
        
        # ------------------------------------------------------------------------
        # Camada 2: LLM Classification (Custo Baixo)
        # ------------------------------------------------------------------------
        # Camada 1 não detectou ameaça óbvia, fazer análise semântica com Flash
        logger.debug("Camada 1 não detectou ameaças, prosseguindo para Camada 2")
        
        layer2_result, tokens_used = self._layer2_llm_classification(user_request)
        
        # Calcular custo evitado se bloqueado pela Camada 2
        cost_avoided = 0.0
        if layer2_result.intent_category == "BLOCKED":
            cost_avoided = self._estimate_cost_avoided(user_request)
            logger.warning(
                f"Camada 2 bloqueou requisição: {layer2_result.intent_category} - "
                f"Riscos: {layer2_result.detected_risks}"
            )
        else:
            logger.info(f"Requisição permitida: {layer2_result.intent_category}")
        
        return GuardrailResult(
            layer="llm_classification",
            classification=layer2_result,
            tokens_used=tokens_used,
            cost_avoided=cost_avoided
        )
    
    def _layer1_pattern_matching(self, user_request: str) -> Optional[IntentClassification]:
        """
        Camada 1: Pattern Matching via regex compilado.
        
        🎯 Aula 03 - Custo Zero:
        Esta camada não consome tokens nem faz chamadas a APIs. É puro
        processamento local via regex, extremamente rápido (<1ms).
        
        Args:
            user_request: Requisição do usuário
            
        Returns:
            IntentClassification se ameaça detectada, None caso contrário
        """
        logger.debug("Executando Camada 1: Pattern Matching")
        
        detected_risks = []
        
        # Verificar cada categoria de ameaça
        for category, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(user_request):
                    detected_risks.append(category)
                    logger.debug(f"Padrão detectado [{category}]: {pattern.pattern}")
                    break  # Um match por categoria é suficiente
        
        # Se nenhum padrão detectado, retornar None (passa para Camada 2)
        if not detected_risks:
            logger.debug("Camada 1: Nenhuma ameaça detectada")
            return None
        
        # Ameaça detectada - criar classificação de bloqueio
        return IntentClassification(
            intent_category="BLOCKED",
            confidence=0.95,  # Alta confiança em pattern matching
            reasoning=(
                f"Padrões de ameaça detectados na requisição: {', '.join(detected_risks)}. "
                "Requisição bloqueada por segurança."
            ),
            detected_risks=detected_risks
        )
    
    def _layer2_llm_classification(self, user_request: str) -> tuple[IntentClassification, int]:
        """
        Camada 2: Classificação via LLM (Gemini Flash).
        
        🎯 Aula 03 - FinOps:
        Usa Gemini Flash (~16x mais barato que Pro) para fazer análise semântica
        profunda da intenção. O custo adicional é mínimo comparado ao custo do
        modelo principal que seria executado se não bloquearmos aqui.
        
        📊 Exemplo de Custos (assumindo 200 tokens input + 100 tokens output):
        - Flash (classificação): ~$0.00006
        - Pro (auditoria principal): ~$0.00125
        - Economia se bloqueado: $0.00119 (20x)
        
        Args:
            user_request: Requisição do usuário
            
        Returns:
            Tupla (IntentClassification, tokens_used)
        """
        logger.debug("Executando Camada 2: LLM Classification")
        
        # Verificar se Camada 2 está habilitada
        llm_config = self.config.get('llm_classification', {})
        if not llm_config.get('enabled', True):
            logger.info("Camada 2 desabilitada, permitindo requisição")
            return IntentClassification(
                intent_category="ALLOWED",
                confidence=0.5,
                reasoning="Camada 2 desabilitada, requisição permitida por padrão",
                detected_risks=[]
            ), 0
        
        # Verificar se estamos em modo USE_MOCK
        use_mock = os.getenv("USE_MOCK", "true").lower() == "true"
        
        if use_mock:
            # Modo simulação: retorna ALLOWED sempre na Camada 2
            logger.debug("Modo simulação: Camada 2 permite requisição")
            return IntentClassification(
                intent_category="ALLOWED",
                confidence=0.85,
                reasoning="Simulação: Requisição analisada semanticamente e considerada segura",
                detected_risks=[]
            ), 50  # Simula ~50 tokens de uso
        
        # Modo real: chamar Vertex AI com Flash via Google GenAI SDK
        if not GENAI_AVAILABLE or self.client is None:
            logger.warning("Google GenAI SDK não disponível, permitindo requisição")
            return IntentClassification(
                intent_category="ALLOWED",
                confidence=0.5,
                reasoning="Google GenAI SDK não disponível, requisição permitida por fallback",
                detected_risks=[]
            ), 0
        
        try:
            # Renderizar template Jinja2
            template = self.jinja_env.get_template("intent_classifier.jinja2")
            prompt = template.render(user_request=user_request)
            
            # Configurar modelo Flash
            model_name = llm_config.get('model', 'gemini-2.5-flash')
            
            # Configurar geração via GenerateContentConfig
            config = types.GenerateContentConfig(
                response_mime_type=llm_config.get('response_mime_type', "application/json"),
                temperature=llm_config.get('temperature', 0.1),
                max_output_tokens=llm_config.get('max_output_tokens', 256),
            )
            
            logger.debug(f"Chamando {model_name} para classificação")
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            
            # Extrair tokens usados (candidates_token_count pode ser None no novo SDK)
            tokens_used = (
                (response.usage_metadata.prompt_token_count or 0) +
                (response.usage_metadata.candidates_token_count or 0)
            )
            
            # Validar resposta JSON com Pydantic
            classification = IntentClassification.model_validate_json(response.text)
            
            logger.info(
                f"Camada 2: {classification.intent_category} "
                f"(confidence: {classification.confidence:.2f}, tokens: {tokens_used})"
            )
            
            return classification, tokens_used
            
        except TemplateNotFound as e:
            logger.error(f"Template não encontrado: {e}")
            # Fallback: permitir requisição se template não existe
            return IntentClassification(
                intent_category="ALLOWED",
                confidence=0.3,
                reasoning="Template de classificação não encontrado, permitindo por fallback",
                detected_risks=[]
            ), 0
        except ValidationError as e:
            logger.error(f"Resposta do LLM não válida: {e}")
            # Fallback: permitir requisição se resposta inválida
            return IntentClassification(
                intent_category="ALLOWED",
                confidence=0.3,
                reasoning="Erro na validação da resposta do classificador, permitindo por fallback",
                detected_risks=[]
            ), 0
        except Exception as e:
            logger.error(f"Erro na Camada 2: {e}", exc_info=True)
            # Fallback: permitir requisição em caso de erro
            return IntentClassification(
                intent_category="ALLOWED",
                confidence=0.3,
                reasoning=f"Erro no classificador: {str(e)}, permitindo por fallback",
                detected_risks=[]
            ), 0
    
    def _estimate_cost_avoided(self, user_request: str) -> float:
        """
        Estima o custo que seria gasto se a requisição bloqueada
        fosse processada pelo modelo principal (Pro).
        
        🎯 Aula 03 - FinOps Metrics:
        Esta métrica demonstra o valor do Guardrail em termos financeiros.
        Pode ser usada em dashboards de FinOps para justificar o investimento
        em segurança ("o guardrail economizou X dólares este mês").
        
        Args:
            user_request: Requisição bloqueada
            
        Returns:
            Custo estimado evitado em USD
        """
        # Estimativa conservadora:
        # - Prompt template: ~500 tokens
        # - User request: ~100 tokens (média)
        # - Resposta: ~150 tokens (média)
        # Total: ~750 tokens
        
        estimated_total_tokens = 750
        
        # Preço do Pro (mais caro, que seria usado sem o guardrail)
        # Valores de referência do model_policy.yaml
        pro_input_cost_per_1k = 0.00125
        pro_output_cost_per_1k = 0.01000
        
        # Assumir 600 tokens input, 150 tokens output
        estimated_cost = (
            (600 / 1000.0) * pro_input_cost_per_1k +
            (150 / 1000.0) * pro_output_cost_per_1k
        )
        
        return round(estimated_cost, 6)
    
    def _sanitize_for_log(self, text: str, max_length: int = None) -> str:
        """
        Sanitiza texto para log aplicando data minimization.
        
        🎯 Aula 03 - Privacy Enhancement:
        Implementa o Defensive Engineering Goal de Data Minimization:
        - Trunca textos longos
        - Remove PII (CPF, email) se configurado
        - Protege dados sensíveis em logs
        
        Args:
            text: Texto a sanitizar
            max_length: Tamanho máximo (default: config ou 200)
            
        Returns:
            Texto sanitizado
        """
        if max_length is None:
            data_min_config = self.config.get('data_minimization', {})
            max_length = data_min_config.get('max_log_length', 200)
        
        # Truncar se muito longo
        if len(text) > max_length:
            text = text[:max_length] + "..."
        
        # Sanitizar PII se configurado
        data_min_config = self.config.get('data_minimization', {})
        if data_min_config.get('sanitize_pii', False):
            pii_patterns = data_min_config.get('pii_patterns', {})
            
            # Sanitizar CPF
            if 'cpf' in pii_patterns:
                cpf_pattern = pii_patterns['cpf']
                text = re.sub(cpf_pattern, '***.***.***-**', text)
            
            # Sanitizar email
            if 'email' in pii_patterns:
                email_pattern = pii_patterns['email']
                text = re.sub(email_pattern, '***@***.***', text)
            
            # Sanitizar telefone
            if 'phone' in pii_patterns:
                phone_pattern = pii_patterns['phone']
                text = re.sub(phone_pattern, '(##) #####-####', text)
        
        return text
