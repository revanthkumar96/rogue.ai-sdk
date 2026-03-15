"""LLM Provider Auto-Instrumentation for Rouge"""

from rouge.config import RougeConfig


def instrument_llm(config: RougeConfig) -> None:
    """
    Automatically instrument LLM providers if their libraries are installed.
    Supported: OpenAI, Anthropic, LangChain.
    """

    # 1. OpenAI Integration
    try:
        from opentelemetry.instrumentation.openai import OpenAIInstrumentor
        OpenAIInstrumentor().instrument()
        if config.tracer_verbose:
            print("[Rouge-Tracer] OpenAI auto-instrumentation enabled.")
    except ImportError:
        pass
    except Exception as e:
        if config.tracer_verbose:
            print(f"[Rouge-Tracer] Failed to instrument OpenAI: {e}")

    # 2. Anthropic Integration
    try:
        from opentelemetry.instrumentation.anthropic import \
            AnthropicInstrumentor
        AnthropicInstrumentor().instrument()
        if config.tracer_verbose:
            print("[Rouge-Tracer] Anthropic auto-instrumentation enabled.")
    except ImportError:
        pass
    except Exception as e:
        if config.tracer_verbose:
            print(f"[Rouge-Tracer] Failed to instrument Anthropic: {e}")

    # 3. LangChain Integration
    try:
        # Note: LangChain instrumentation usually requires the provider-spec
        # instrumentors to be active as well for full trace context.
        from opentelemetry.instrumentation.langchain import \
            LangChainInstrumentor
        LangChainInstrumentor().instrument()
        if config.tracer_verbose:
            print("[Rouge-Tracer] LangChain auto-instrumentation enabled.")
    except ImportError:
        pass
    except Exception as e:
        if config.tracer_verbose:
            print(f"[Rouge-Tracer] Failed to instrument LangChain: {e}")
