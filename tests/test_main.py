"""
Testes Unitários - Funções do main.py e gateway.py (Aula 03)
"""

import pytest
from pathlib import Path
from src.gateway import render_prompt_template, simulate_llm_response, simulate_input_output


class TestPromptTemplate:
    """Testes para processamento de templates Jinja2."""
    
    def test_render_prompt_template(self):
        """Testa renderização de template Jinja2."""
        user_request = "Teste de solicitação"
        prompt = render_prompt_template(user_request)
        
        # Verifica que o prompt foi processado
        assert len(prompt) > 0
        # Verifica que a solicitação do usuário está no prompt
        assert user_request in prompt
        # Verifica que não há placeholders não substituídos
        assert "{{ user_request }}" not in prompt
    
    def test_render_prompt_template_with_special_chars(self):
        """Testa renderização com caracteres especiais."""
        user_request = "Teste com 'aspas' e \"aspas duplas\""
        prompt = render_prompt_template(user_request)
        
        assert user_request in prompt
    
    def test_render_prompt_template_missing_file(self):
        """Testa erro com arquivo de template inexistente."""
        # Jinja2 pode lançar TemplateNotFound ou ValueError
        with pytest.raises((FileNotFoundError, ValueError)):
            render_prompt_template("teste", "prompts/nonexistent.jinja2")


class TestSimulateLLMResponse:
    """Testes para simulação de resposta do LLM."""
    
    def test_simulate_llm_response_transfer(self):
        """Testa simulação de resposta para transferência."""
        response = simulate_llm_response(
            "gemini-1.5-pro-001",
            "Preciso fazer uma transferência"
        )
        
        assert "compliance_status" in response
        assert "risk_level" in response
        assert "audit_reasoning" in response
        assert response["compliance_status"] == "REQUIRES_REVIEW"
    
    def test_simulate_llm_response_consultation(self):
        """Testa simulação de resposta para consulta."""
        response = simulate_llm_response(
            "gemini-1.5-pro-001",
            "Consultar saldo"
        )
        
        assert response["compliance_status"] == "APPROVED"
        assert response["risk_level"] == "LOW"
    
    def test_simulate_llm_response_deletion(self):
        """Testa simulação de resposta para exclusão."""
        # Testa com diferentes variações da palavra exclusão
        for request in ["Excluir dados", "exclusão de registros", "delete files", "remover dados"]:
            response = simulate_llm_response(
                "gemini-1.5-pro-001",
                request
            )
            
            assert response["compliance_status"] == "REJECTED"
            assert response["risk_level"] == "HIGH"
    
    def test_simulate_llm_response_pro_vs_flash(self):
        """Testa diferença entre respostas Pro e Flash."""
        response_pro = simulate_llm_response(
            "gemini-1.5-pro-001",
            "Consulta genérica"
        )
        
        response_flash = simulate_llm_response(
            "gemini-1.5-flash-001",
            "Consulta genérica"
        )
        
        # Pro deve ter reasoning mais longo
        assert len(response_pro["audit_reasoning"]) > len(response_flash["audit_reasoning"])


class TestSimulateInputOutput:
    """Testes para simulação de input/output."""
    
    def test_simulate_input_output(self):
        """Testa cálculo de tamanho de input/output."""
        user_request = "Teste de solicitação"
        model_response = {
            "compliance_status": "APPROVED",
            "risk_level": "LOW",
            "audit_reasoning": "Teste de reasoning"
        }
        
        input_chars, output_chars = simulate_input_output(user_request, model_response)
        
        assert input_chars > 0
        assert output_chars > 0
        # Input deve incluir o template + request
        assert input_chars > len(user_request)
        # Output deve incluir o JSON da resposta
        assert output_chars > 0
    
    def test_simulate_input_output_proportional(self):
        """Testa que tamanhos são proporcionais."""
        short_request = "Curto"
        long_request = "Esta é uma solicitação muito mais longa com mais detalhes"
        
        response = {
            "compliance_status": "APPROVED",
            "risk_level": "LOW",
            "audit_reasoning": "Teste"
        }
        
        input_short, _ = simulate_input_output(short_request, response)
        input_long, _ = simulate_input_output(long_request, response)
        
        assert input_long > input_short

