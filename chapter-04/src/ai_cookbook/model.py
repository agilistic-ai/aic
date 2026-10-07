"""One provider boundary; responses remain untrusted until application validation."""

import os
from contextlib import closing
from dataclasses import dataclass
from time import perf_counter

from .settings import ConfigurationError, load_settings


class GenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModelReply:
    text: str
    model: str
    input_tokens: int | None
    output_tokens: int | None
    provider: str | None = None
    elapsed_seconds: float = 0.0
    config_sha256: str | None = None


def _count(value):
    return value if type(value) is int and value >= 0 else None


def _hosted(settings, instructions, note, schema, limit, stream):
    from openai import OpenAI

    key = os.environ.get("AIC_API_KEY", "").strip()
    if not key:
        raise ConfigurationError("Set AIC_API_KEY for hosted inference.")
    with OpenAI(api_key=key, base_url=settings.base_url,
                timeout=settings.timeout_seconds, max_retries=0) as client:
        request = dict(model=settings.name, instructions=instructions,
                       input=[{"role": "user", "content": note}],
                       text={"format": {"type": "json_schema", "name": "result",
                                        "strict": True, "schema": schema}},
                       max_output_tokens=limit, store=False, truncation="disabled")
        if stream:
            response = None
            with client.responses.create(**request, stream=True) as events:
                for event in events:
                    if event.type == "response.completed":
                        response = event.response
                    elif event.type in {"response.failed", "response.incomplete", "error"}:
                        raise GenerationError("The provider did not complete the response.")
            if response is None:
                raise GenerationError("The response stream ended before completion.")
        else:
            response = client.responses.create(**request)
        if response.status != "completed":
            raise GenerationError("The provider did not complete the response.")
        for output in response.output:
            if output.type != "message":
                raise GenerationError("Unexpected provider output.")
            for part in output.content:
                if part.type != "output_text":
                    raise GenerationError("The provider declined or returned unexpected content.")
        usage = response.usage
        return (response.output_text, response.model or settings.name,
                _count(usage.input_tokens) if usage else None,
                _count(usage.output_tokens) if usage else None)


def _local(settings, instructions, note, schema, limit, context, stream):
    from ollama import Client

    with closing(Client(host=settings.base_url, timeout=settings.timeout_seconds)) as client:
        request = dict(model=settings.name,
                       messages=[{"role": "system", "content": instructions},
                                 {"role": "user", "content": note}],
                       format=schema, stream=stream,
                       options={"temperature": 0, "num_predict": limit, "num_ctx": context})
        response = client.chat(**request)
        if stream:
            pieces, final, size = [], None, 0
            with closing(response) as events:
                for part in events:
                    if part.message.tool_calls:
                        raise GenerationError("This application does not accept tool calls.")
                    piece = part.message.content or ""
                    size += len(piece.encode("utf-8"))
                    if size > 65536:
                        raise GenerationError("Provider output exceeded the limit.")
                    pieces.append(piece)
                    if part.done:
                        final = part
            response, text = final, "".join(pieces)
        else:
            if response.message.tool_calls:
                raise GenerationError("This application does not accept tool calls.")
            text = response.message.content
        if response is None or not response.done or response.done_reason != "stop":
            raise GenerationError("The local model did not complete the response.")
        return (text, response.model or settings.name,
                _count(response.prompt_eval_count), _count(response.eval_count))


def generate(instructions, note, schema, *, max_output_tokens=512,
             context_tokens=4096, settings=None, stream=False):
    settings = settings or load_settings()
    if type(max_output_tokens) is not int or not 1 <= max_output_tokens <= 16384:
        raise ValueError("Invalid output token allowance.")
    if type(context_tokens) is not int or context_tokens <= max_output_tokens:
        raise ValueError("Context must exceed the output token allowance.")
    started = perf_counter()
    try:
        if settings.provider == "openai":
            result = _hosted(settings, instructions, note, schema, max_output_tokens, stream)
        elif settings.provider == "ollama":
            result = _local(settings, instructions, note, schema, max_output_tokens, context_tokens, stream)
        else:
            raise ConfigurationError("Unsupported model provider.")
    except (ConfigurationError, GenerationError):
        raise
    except ImportError:
        raise ConfigurationError("Install the project's locked dependencies.") from None
    except Exception:
        # SDK errors can contain request text, response bodies, or endpoint details.
        raise GenerationError("Model request failed; check service access and timeout settings.") from None
    text, model, incoming, outgoing = result
    if not isinstance(text, str) or not text.strip() or len(text.encode("utf-8")) > 65536:
        raise GenerationError("The provider returned empty or oversized text.")
    return ModelReply(text, model, incoming, outgoing, settings.provider,
                      perf_counter() - started, settings.fingerprint)
