"""The single boundary between this project and the LLM providers.

Like github_client.py isolates GitHub, this isolates the model provider.
Everything else asks this module for findings; nothing else imports a
provider SDK. That seam is what lets the Week 7 benchmark swap providers as
a config change (pass a different `client`), and what lets us mock the model
in tests.

Three providers are supported, dispatched by the type of `client` passed in:
  - google.genai.Client   -> Gemini   (response_schema structured output)
  - anthropic.Anthropic   -> Claude   (messages.parse structured output)
  - openai.OpenAI         -> GPT       (chat.completions.parse structured output)

Callers do not choose a provider explicitly; they simply hand in the client
they constructed. `build_graph` and the agents are unchanged — only the
client object handed to build_graph differs between providers.
"""

import time

from google import genai
from google.genai import types
from pydantic import BaseModel, TypeAdapter

from anthropic import Anthropic
from openai import OpenAI

# --------------------------------------------------------------------------- #
# Transient-error retry, shared shape across providers.
#   Anthropic: 529 "overloaded". OpenAI: 429 rate limit / 503. Gemini has its
#   own retry in run_eval_raw; here we cover the paid providers' transient codes.
# --------------------------------------------------------------------------- #
_MAX_RETRIES = 4
_BASE_BACKOFF = 5
_TRANSIENT = ("529", "overloaded", "rate_limit", "429", "503", "overloaded_error")

# Anthropic and OpenAI both want an OBJECT schema for structured output, not a
# bare list. The Gemini path uses list[schema] directly; for the other two we
# wrap the list in a container model, then unwrap. Built once per schema, cached.
_LIST_WRAPPERS: dict[type, type[BaseModel]] = {}


def _list_wrapper(schema: type[BaseModel]) -> type[BaseModel]:
    """Return a cached `{items: list[schema]}` container model."""
    if schema not in _LIST_WRAPPERS:
        _LIST_WRAPPERS[schema] = type(
            f"{schema.__name__}ListWrapper",
            (BaseModel,),
            {"__annotations__": {"items": list[schema]}},
        )
    return _LIST_WRAPPERS[schema]


def _is_transient(exc: Exception) -> bool:
    text = str(exc)
    return any(marker in text for marker in _TRANSIENT)


# --------------------------------------------------------------------------- #
# Anthropic backend
# --------------------------------------------------------------------------- #
def _anthropic_parse(
    *, client: Anthropic, model: str, system_prompt: str,
    user_content: str, output_format: type[BaseModel],
) -> BaseModel:
    last_exc = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            response = client.messages.parse(
                model=model,
                max_tokens=4096,
                system=system_prompt,
                messages=[{"role": "user", "content": user_content}],
                output_format=output_format,
                temperature=0,
            )
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if not _is_transient(e) or attempt == _MAX_RETRIES:
                raise
            time.sleep(_BASE_BACKOFF * (2 ** (attempt - 1)))
            continue

        stop = getattr(response, "stop_reason", None)
        if stop == "refusal":
            raise RuntimeError(f"Anthropic refused (model={model}).")
        if stop == "max_tokens":
            raise RuntimeError(f"Anthropic output truncated at max_tokens (model={model}).")
        return response.parsed_output
    raise last_exc


# --------------------------------------------------------------------------- #
# OpenAI backend
# --------------------------------------------------------------------------- #
def _openai_parse(
    *, client: OpenAI, model: str, system_prompt: str,
    user_content: str, output_format: type[BaseModel],
) -> BaseModel:
    last_exc = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            completion = client.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content},
                ],
                response_format=output_format,
                temperature=0,
            )
        except Exception as e:  # noqa: BLE001
            last_exc = e
            if not _is_transient(e) or attempt == _MAX_RETRIES:
                raise
            time.sleep(_BASE_BACKOFF * (2 ** (attempt - 1)))
            continue

        msg = completion.choices[0].message
        # Structured outputs add a first-class refusal path — handle it.
        if getattr(msg, "refusal", None):
            raise RuntimeError(f"OpenAI refused (model={model}): {msg.refusal}")
        parsed = msg.parsed
        if parsed is None:
            raise RuntimeError(f"OpenAI returned no parsed output (model={model}).")
        return parsed
    raise last_exc


# --------------------------------------------------------------------------- #
# Public interface — unchanged signatures. Provider inferred from client type.
# --------------------------------------------------------------------------- #
def generate_findings(
    *, client, model: str, system_prompt: str,
    user_content: str, schema: type[BaseModel],
) -> list:
    """Call the model with structured output and return a validated list.

    The provider's schema constraint is a strong hint; our Pydantic validation
    is the law. We re-validate the returned data against `schema` ourselves.
    """
    if isinstance(client, Anthropic):
        wrapper = _list_wrapper(schema)
        parsed = _anthropic_parse(
            client=client, model=model, system_prompt=system_prompt,
            user_content=user_content, output_format=wrapper,
        )
        return TypeAdapter(list[schema]).validate_python(
            [item.model_dump() for item in parsed.items]
        )

    if isinstance(client, OpenAI):
        wrapper = _list_wrapper(schema)
        parsed = _openai_parse(
            client=client, model=model, system_prompt=system_prompt,
            user_content=user_content, output_format=wrapper,
        )
        return TypeAdapter(list[schema]).validate_python(
            [item.model_dump() for item in parsed.items]
        )

    # Default: Gemini.
    response = client.models.generate_content(
        model=model,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=list[schema],
            temperature=0,
        ),
    )
    return TypeAdapter(list[schema]).validate_json(response.text)


def generate_structured(
    *, client, model: str, system_prompt: str,
    user_content: str, schema: type[BaseModel],
) -> BaseModel:
    """Call the model with structured output and return one validated object."""
    if isinstance(client, Anthropic):
        parsed = _anthropic_parse(
            client=client, model=model, system_prompt=system_prompt,
            user_content=user_content, output_format=schema,
        )
        return schema.model_validate(parsed.model_dump())

    if isinstance(client, OpenAI):
        parsed = _openai_parse(
            client=client, model=model, system_prompt=system_prompt,
            user_content=user_content, output_format=schema,
        )
        return schema.model_validate(parsed.model_dump())

    # Default: Gemini.
    response = client.models.generate_content(
        model=model,
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0,
        ),
    )
    return schema.model_validate_json(response.text)