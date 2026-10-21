"""Customer-facing messages shared by the CLI and the web UI."""

from __future__ import annotations

import anthropic


def api_error_message(exc: anthropic.APIError) -> str:
    if isinstance(exc, anthropic.AuthenticationError):
        return "Acesso negado: confira EMPORIO_ACCESS_CODE (modo proxy) ou ANTHROPIC_API_KEY (modo direto)."
    if isinstance(exc, anthropic.RateLimitError):
        return "Muitas mensagens em pouco tempo. Aguarde um minuto e tente de novo."
    if isinstance(exc, anthropic.PermissionDeniedError):
        return "O limite de uso da demonstração foi atingido. Tente mais tarde ou use sua própria chave da API."
    if isinstance(exc, anthropic.APIConnectionError):
        return "Não consegui conectar ao servidor. Verifique sua internet e tente de novo."
    return f"Erro ao falar com o modelo ({type(exc).__name__}). Tente de novo."
