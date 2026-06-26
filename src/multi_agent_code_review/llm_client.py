"""The single boundary between this project and the Gemini API.

Like github_client.py isolates GitHub, this isolates the LLM provider.
Everything else asks this module for findings; nothing else imports the
provider SDK. That seam is what lets us swap providers in Week 7 as a
config change, and what lets us mock the model in tests.
"""

from google import genai
from google.genai import types
from pydantic import BaseModel, TypeAdapter


def generate_findings(
    *,
    client: genai.Client,
    model: str,
    system_prompt: str,
    user_content: str,
    schema: type[BaseModel],
) -> list:
    """Call Gemini with structured output and return validated objects.

    The model is constrained to return a JSON list matching `schema`. We then
    re-validate that JSON against `schema` ourselves: the provider's
    constraint is a strong hint, but our Pydantic validation is the law.
    """
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
    *,
    client: genai.Client,
    model: str,
    system_prompt: str,
    user_content: str,
    schema: type[BaseModel],
) -> BaseModel:
    """Call Gemini with structured output and return one validated object."""
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