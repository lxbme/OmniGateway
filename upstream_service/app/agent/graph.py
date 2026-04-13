from langgraph.graph import END, START, StateGraph

from app.agent.nodes import input_node, llm_node, output_node
from app.agent.state import AgentState


graph_builder = StateGraph(AgentState)
graph_builder.add_node("input_node", input_node)
graph_builder.add_node("llm_node", llm_node)
graph_builder.add_node("output_node", output_node)

graph_builder.add_edge(START, "input_node")
graph_builder.add_edge("input_node", "llm_node")
graph_builder.add_edge("llm_node", "output_node")
graph_builder.add_edge("output_node", END)

graph_app = graph_builder.compile()
