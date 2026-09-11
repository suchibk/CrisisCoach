# Shared orchestration

WorkflowEngine owns lifecycle, timer scheduling, controls, and atomic repository commits. DomainPack owns opening/recovery instructions, safety policy, silence policy, clearance, and the next domain action. The engine imports no collision rules.

TurnGraph uses Pydantic TurnState and explicit conditional routing: safety -> controls -> gate -> plan. A handled response exits immediately. Local and optional LangGraph execution use the same node functions and next-node function. Accepted transitions persist GRAPH_ROUTE records. Safety pre-emption precedes control routing, including while paused.

The default local backend preserves dependency-light offline operation. Set CRISIS_COACH_GRAPH_BACKEND=langgraph with the agent extra installed for StateGraph execution. A missing requested backend raises an error; it never silently switches runners. Model output cannot choose a node.

SQLite owns turn-level durability. No LangGraph checkpointer is configured: graph nodes have no external actions, and the completed turn is committed atomically. Tool approval interrupts and durable graph checkpoints remain future work.
