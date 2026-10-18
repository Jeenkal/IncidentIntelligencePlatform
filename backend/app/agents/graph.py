from langgraph.graph import END, START, StateGraph

from app.agents.state import InvestigationState

from app.agents.investigator import (
    retrieve_evidence,
    generate_hypotheses,
    verify_hypotheses,
    refine_investigation_query,
    should_retry_after_retrieval,
    should_retry_after_verification,
)


def build_investigation_graph():
    graph = StateGraph(InvestigationState)

    graph.add_node("retrieve_evidence", retrieve_evidence)
    graph.add_node("generate_hypotheses", generate_hypotheses)
    graph.add_node("verify_hypotheses", verify_hypotheses)
    graph.add_node("refine_query", refine_investigation_query)

    graph.add_edge(START, "retrieve_evidence")

    graph.add_conditional_edges(
        "retrieve_evidence",
        should_retry_after_retrieval,
        {
            "generate_hypotheses": "generate_hypotheses",
            "refine_query": "refine_query",
            "verify_hypotheses": "verify_hypotheses",
        },
    )

    graph.add_edge(
        "generate_hypotheses",
        "verify_hypotheses",
    )

    graph.add_conditional_edges(
        "verify_hypotheses",
        should_retry_after_verification,
        {
            "refine_query": "refine_query",
            "finish": END,
        },
    )

    graph.add_edge("refine_query", "retrieve_evidence")

    return graph.compile()


investigation_graph = build_investigation_graph()