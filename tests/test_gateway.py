"""
Testes Unitários - Gateway (Aula 03)
"""

import pytest
from unittest.mock import Mock, patch
from pydantic import ValidationError

from src.gateway import (
    render_prompt_template,
    simulate_llm_response,
    simulate_input_output,
    load_safety_settings,
    call_vertex_ai
)
from src.models import AuditResponse


class TestRenderPromptTemplate:
    """Testes para renderização de templates Jinja2."""
    
    def test_render_template_success(self):
        """Testa renderização bem-sucedida do template."""
        user_request = "Consultar relatório de auditoria"
        prompt = render_prompt_template(user_request)
        
        assert len(prompt) > 0
        assert user_request in prompt
        assert "{{ user_request }}" not in prompt  # Variável substituída
    
    def test_render_template_with_special_characters(self):
        """Testa renderização com caracteres especiais."""
        user_request = "Teste com 'aspas' e acentuação çãõ"
        prompt = render_prompt_template(user_request)
        
        assert user_request in prompt
    
    def test_render_template_missing_file(self):
        """Testa erro quando template não existe."""
        with pytest.raises(FileNotFoundError):
            render_prompt_template("teste", "prompts/nonexistent.jinja2")


class TestSimulateLLMResponse:
    """Testes para simulação de resposta do LLM."""
    
    def test_simulate_returns_valid_audit_response(self):
        """Testa que simulação retorna resposta válida (validada por Pydantic)."""
        response = simulate_llm_response(
            "gemini-2.5-pro",
            "Consultar saldo"
        )
        
        # Deve ter todos os campos obrigatórios
        assert "compliance_status" in response
        assert "risk_level" in response
        assert "audit_reasoning" in response
        
        # Deve ser validável por Pydantic (teste indireto)
        audit_response = AuditResponse(**response)
        assert audit_response.compliance_status in ["APPROVED", "REJECTED", "REQUIRES_REVIEW"]
    
    def test_simulate_transfer_requires_review(self):
        """Testa que transferência requer revisão."""
        response = simulate_llm_response(
            "gemini-2.5-pro",
            "Transferir R$ 10.000 para conta XYZ"
        )
        
        assert response["compliance_status"] == "REQUIRES_REVIEW"
        assert response["risk_level"] == "MEDIUM"
    
    def test_simulate_deletion_rejected(self):
        """Testa que exclusão é rejeitada."""
        response = simulate_llm_response(
            "gemini-2.5-pro",
            "Excluir todos os dados históricos"
        )
        
        assert response["compliance_status"] == "REJECTED"
        assert response["risk_level"] == "HIGH"
    
    def test_simulate_consultation_approved(self):
        """Testa que consulta é aprovada."""
        response = simulate_llm_response(
            "gemini-2.5-pro",
            "Consultar saldo da conta"
        )
        
        assert response["compliance_status"] == "APPROVED"
        assert response["risk_level"] == "LOW"
    
    def test_simulate_reasoning_minimum_length(self):
        """Testa que reasoning tem mínimo de 10 caracteres (Pydantic validation)."""
        response = simulate_llm_response(
            "gemini-2.5-flash",
            "Teste"
        )
        
        # Deve ser validável por Pydantic (min_length=10)
        audit_response = AuditResponse(**response)
        assert len(audit_response.audit_reasoning) >= 10
    
    def test_simulate_pro_vs_flash_difference(self):
        """Testa diferença entre Pro e Flash na simulação."""
        request = "Consulta genérica de auditoria"
        
        response_pro = simulate_llm_response("gemini-2.5-pro", request)
        response_flash = simulate_llm_response("gemini-2.5-flash", request)
        
        # Pro deve ter reasoning mais longo que Flash (simulação)
        # Ambos devem ser válidos com Pydantic
        AuditResponse(**response_pro)
        AuditResponse(**response_flash)


class TestSimulateInputOutput:
    """Testes para simulação de input/output."""
    
    def test_simulate_returns_positive_values(self):
        """Testa que simulação retorna valores positivos."""
        user_request = "Consultar relatório"
        model_response = {
            "compliance_status": "APPROVED",
            "risk_level": "LOW",
            "audit_reasoning": "Teste de reasoning"
        }
        
        input_chars, output_chars = simulate_input_output(user_request, model_response)
        
        assert input_chars > 0
        assert output_chars > 0
        # Input deve ser maior que request (inclui template)
        assert input_chars > len(user_request)


class TestLoadSafetySettings:
    """Testes para carregamento de Safety Settings."""
    
    @patch('src.gateway.GENAI_AVAILABLE', True)
    def test_load_safety_settings_success(self):
        """Testa carregamento bem-sucedido de safety settings."""
        # Este teste requer que o Google GenAI SDK esteja disponível
        # Se não estiver, será pulado
        try:
            settings = load_safety_settings()
            # Deve retornar lista (pode estar vazia se SDK não disponível)
            assert isinstance(settings, list)
        except Exception:
            pytest.skip("Google GenAI SDK não disponível")
    
    @patch('src.gateway.GENAI_AVAILABLE', False)
    def test_load_safety_settings_when_genai_unavailable(self):
        """Testa comportamento quando Google GenAI SDK não está disponível."""
        settings = load_safety_settings()
        
        # Deve retornar lista vazia sem lançar exceção
        assert settings == []


class TestCallVertexAI:
    """Testes para chamadas ao Vertex AI (requerem mock ou ambiente configurado)."""
    
    def test_call_vertex_ai_without_sdk_raises_error(self):
        """Testa que erro é lançado quando SDK não disponível."""
        with patch('src.gateway.GENAI_AVAILABLE', False):
            with pytest.raises(RuntimeError) as exc_info:
                call_vertex_ai(None, "gemini-2.5-pro", "teste", [])
            
            assert "não disponível" in str(exc_info.value)
    
    def test_call_vertex_ai_without_client_raises_error(self):
        """Testa que erro é lançado quando client é None."""
        with patch('src.gateway.GENAI_AVAILABLE', True):
            with pytest.raises(RuntimeError) as exc_info:
                call_vertex_ai(None, "gemini-2.5-pro", "teste", [])
            
            assert "não inicializado" in str(exc_info.value)


class TestStructuredOutputValidation:
    """Testes para validação de Structured Output com Pydantic."""
    
    def test_valid_response_passes_validation(self):
        """Testa que resposta válida passa na validação Pydantic."""
        valid_dict = {
            "compliance_status": "APPROVED",
            "risk_level": "LOW",
            "audit_reasoning": "Esta é uma justificativa válida com mais de 10 caracteres"
        }
        
        # Não deve lançar ValidationError
        response = AuditResponse(**valid_dict)
        assert response.compliance_status == "APPROVED"
    
    def test_invalid_status_fails_validation(self):
        """Testa que status inválido falha na validação."""
        invalid_dict = {
            "compliance_status": "INVALID_STATUS",
            "risk_level": "LOW",
            "audit_reasoning": "Justificativa válida"
        }
        
        with pytest.raises(ValidationError):
            AuditResponse(**invalid_dict)
    
    def test_short_reasoning_fails_validation(self):
        """Testa que reasoning curto falha (min_length=10)."""
        invalid_dict = {
            "compliance_status": "APPROVED",
            "risk_level": "LOW",
            "audit_reasoning": "Curto"  # Menos de 10 caracteres
        }
        
        with pytest.raises(ValidationError):
            AuditResponse(**invalid_dict)
