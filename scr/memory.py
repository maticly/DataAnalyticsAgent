class ConversationMemory:
    """Manages conversation history (short-term memory)."""

    def __init__(self, max_turns: int = 50):
        self.max_turns = max_turns
        self.turns: deque = deque(maxlen=max_turns)

    def add_turn(self, query: str, thought: str, action: str, action_params: Dict, result: str):
        self.turns.append({
            "query": query,
            "thought": thought,
            "action": action,
            "parameters": action_params,
            "result": result
        })

    def get_recent_context(self, last_n: int = 3) -> str:
        if not self.turns:
            return "## Recent Context\n\nNo previous conversation."

        recent = list(self.turns)[-last_n:]
        parts = ["## Recent Context\n"]

        for i, turn in enumerate(recent, 1):
            parts.append(f"**Turn {i}:**")
            parts.append(f"- Thought: {turn['thought'][:200]}...")
            parts.append(f"- Action: {turn['action']}")
            parts.append(f"- Result: {turn['result'][:300]}...\n")

        return "\n".join(parts)

    def clear(self):
        self.turns.clear()
