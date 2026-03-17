"""LLM Provider Auto-Instrumentation for Rouge"""

from rouge.config import RougeConfig


def instrument_llm(config: RougeConfig) -> None:
    """
    Automatically instrument LLM providers if their libraries are installed.
    Supported: OpenAI, Anthropic, Cohere, Mistral AI, Vertex AI, AWS Bedrock,
    Replicate, Google Generative AI, LangChain, LlamaIndex.
    """
    if not config.instrument_llm:
        if config.tracer_verbose:
            print("[Rouge-Tracer] LLM auto-instrumentation is disabled.")
        return

    def _should_instrument(provider_name: str) -> bool:
        if config.llm_providers is None:
            return True
        return provider_name.lower() in [
            p.lower() for p in config.llm_providers
        ]

    # Helper for instrumentation
    def _instrument(name: str, module_path: str, class_name: str):
        if not _should_instrument(name):
            return
        try:
            # Import dynamically to avoid requirement errors
            module = __import__(module_path, fromlist=[class_name])
            instrumentor_class = getattr(module, class_name)
            instrumentor_class().instrument()
            if config.tracer_verbose:
                print(f"[Rouge-Tracer] {name} auto-instrumentation enabled.")
        except ImportError:
            pass
        except Exception as e:
            if config.tracer_verbose:
                print(f"[Rouge-Tracer] Failed to instrument {name}: {e}")

    # 1. OpenAI
    _instrument("OpenAI", "opentelemetry.instrumentation.openai",
                "OpenAIInstrumentor")

    # 2. Anthropic
    _instrument("Anthropic", "opentelemetry.instrumentation.anthropic",
                "AnthropicInstrumentor")

    # 3. Cohere
    _instrument("Cohere", "opentelemetry.instrumentation.cohere",
                "CohereInstrumentor")

    # 4. Mistral AI
    _instrument("Mistral", "opentelemetry.instrumentation.mistralai",
                "MistralAiInstrumentor")

    # 5. Vertex AI
    _instrument("VertexAI", "opentelemetry.instrumentation.vertexai",
                "VertexAIInstrumentor")

    # 6. AWS Bedrock
    _instrument("Bedrock", "opentelemetry.instrumentation.bedrock",
                "BedrockInstrumentor")

    # 7. Replicate
    _instrument("Replicate", "opentelemetry.instrumentation.replicate",
                "ReplicateInstrumentor")

    # 8. Google Generative AI
    _instrument("GoogleGenerativeAI",
                "opentelemetry.instrumentation.google_generativeai",
                "GoogleGenerativeAiInstrumentor")

    # 9. LangChain
    _instrument("LangChain", "opentelemetry.instrumentation.langchain",
                "LangChainInstrumentor")

    # 10. LlamaIndex
    _instrument("LlamaIndex", "opentelemetry.instrumentation.llamaindex",
                "LlamaIndexInstrumentor")
