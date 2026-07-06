"""LangGraph orchestration: fan out to the three specialists in parallel,
merge their findings, then run the deterministic filter pipeline.


"""

import operator
from typing import Annotated, TypedDict

from google import genai
from langgraph.graph import END, START, StateGraph

from multi_agent_code_review.agents.coverage import review_test_coverage
from multi_agent_code_review.agents.maintainability import review_maintainability
from multi_agent_code_review.agents.security import review_security
from multi_agent_code_review.filters.pipeline import apply_filters
from multi_agent_code_review.schemas import Category, Finding
from multi_agent_code_review.agents.synthesizer import synthesize

class ReviewState(TypedDict):
    diff: str
    findings: Annotated[list[Finding], operator.add]
    filtered: list[Finding]
    comment: str


def _stamp(findings: list[Finding], category: Category) -> list[Finding]:
    return [f.model_copy(update={"category": category}) for f in findings]


def build_graph(
    *, client: genai.Client, specialist_model: str, synthesizer_model: str
):
    """Compile the review graph.

    Specialists run on `specialist_model` (cheap tier); the synthesizer runs on
    `synthesizer_model` (premium tier). Splitting the two is what lets the
    benchmark pair cheap specialists with a premium synthesizer per provider.
    """

    def security_node(state: ReviewState) -> dict:
        found = review_security(client=client, model=specialist_model, diff=state["diff"])
        return {"findings": _stamp(found, Category.SECURITY)}

    def maintainability_node(state: ReviewState) -> dict:
        found = review_maintainability(client=client, model=specialist_model, diff=state["diff"])
        return {"findings": _stamp(found, Category.MAINTAINABILITY)}

    def coverage_node(state: ReviewState) -> dict:
        found = review_test_coverage(client=client, model=specialist_model, diff=state["diff"])
        return {"findings": _stamp(found, Category.TEST_COVERAGE)}

    def filter_node(state: ReviewState) -> dict:
        return {"filtered": apply_filters(state["findings"], diff=state["diff"])}

    def synthesizer_node(state: ReviewState) -> dict:
        comment = synthesize(
            client=client,
            model=synthesizer_model,
            diff=state["diff"],
            findings=state["filtered"],
        )
        return {"comment": comment}

    builder = StateGraph(ReviewState)
    builder.add_node("security", security_node)
    builder.add_node("maintainability", maintainability_node)
    builder.add_node("coverage", coverage_node)
    builder.add_node("filter", filter_node)
    builder.add_node("synthesizer", synthesizer_node)

    builder.add_edge(START, "security")          # fan-out
    builder.add_edge(START, "maintainability")
    builder.add_edge(START, "coverage")
    builder.add_edge("security", "filter")       # fan-in
    builder.add_edge("maintainability", "filter")
    builder.add_edge("coverage", "filter")
    builder.add_edge("filter", "synthesizer")    # filtered findings -> one comment
    builder.add_edge("synthesizer", END)

    return builder.compile()