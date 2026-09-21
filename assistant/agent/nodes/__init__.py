"""Node functions for the SRE on-call graph -- one module per node.

Nothing to implement in this file; graph.py imports each node function
directly (`from .nodes.planner import planner_node`, etc.) and wires it
into the StateGraph with `.add_node(name, fn)`. Unlike tools/__init__.py,
there's no registration side effect needed here -- a node only becomes
part of the graph once graph.py explicitly adds it.
"""
