# app/graph/lg_workflow.py

from langgraph.graph import StateGraph, START, END

from app.graph.lg_state import GraphState
from app.graph.nodes import (
    keyword_planner_node,
    serp_node,
    parser_node,
    analyzer_node,
)


def build_graph():
    builder = StateGraph(GraphState)

    # ノード登録
    builder.add_node("keyword_planner", keyword_planner_node)
    builder.add_node("serp", serp_node)
    builder.add_node("parser", parser_node)
    builder.add_node("analyzer", analyzer_node)

    # エッジ定義
    builder.add_edge(START, "keyword_planner")
    builder.add_edge("keyword_planner", "serp")
    builder.add_edge("serp", "parser")
    builder.add_edge("parser", "analyzer")
    builder.add_edge("analyzer", END)

    app = builder.compile()
    return app


# FastAPI から利用する LangGraph アプリ
graph_app = build_graph()
