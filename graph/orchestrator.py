"""LangGraph orchestrator - skill-based voice agent workflow.

Flow: START -> skill_router -> skill_executor -> memory_extractor -> END
"""

from langgraph.graph import StateGraph, END

from graph.state import AgentState
from graph.nodes.skill_router import skill_router
from graph.nodes.skill_executor import skill_executor
from graph.nodes.memory_extractor import memory_extractor


def build_graph() -> StateGraph:
    """Build and compile the voice agent LangGraph."""
    graph = StateGraph(AgentState)

    graph.add_node("skill_router", skill_router)
    graph.add_node("skill_executor", skill_executor)
    graph.add_node("memory_extractor", memory_extractor)

    graph.set_entry_point("skill_router")
    graph.add_edge("skill_router", "skill_executor")
    graph.add_edge("skill_executor", "memory_extractor")
    graph.add_edge("memory_extractor", END)

    return graph.compile()


# Singleton compiled graph
workflow = build_graph()
