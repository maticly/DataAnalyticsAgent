logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AnalyzeTool(BaseTool):
    def __init__(self, llm_client, executor: SafeCodeExecutor, retry_delay: float = 2.0, max_retries: int = 3):
        self.llm = llm_client
        self.executor = executor
        self.retry_delay = retry_delay
        self.max_retries = max_retries

    @property
    def name(self) -> str:
        return "analyze"

    @property
    def description(self) -> str:
        return "Generate and execute pandas code for data analysis."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "dataset_aliases": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["query", "dataset_aliases"]
        }

    def execute(self, query: str, dataset_aliases: list) -> Dict[str, Any]:
        prompt = self._build_prompt(query, dataset_aliases)

        for attempt in range(self.max_retries):
            try:
                response = self.llm.generate_content(prompt)
                code = self._extract_code(response.text)
                if not code:
                    return {"status": "error", "error_message": "Failed to generate code"}

                result = self.executor.execute(code)
                if result["status"] == "success":
                    result["generated_code"] = code
                return result
            except Exception as e:
                if "429" in str(e).lower() or "rate limit" in str(e).lower():
                    if attempt < self.max_retries - 1:
                        wait = self.retry_delay * (2 ** attempt)
                        logger.warning(f"Rate limit. Retrying in {wait}s...")
                        time.sleep(wait)
                        continue
                return {"status": "error", "error_message": str(e)}

        return {"status": "error", "error_message": "Failed after retries"}

    def _build_prompt(self, query: str, aliases: list) -> str:
        ds_info = [f"- {a}: {list(self.executor.datasets[a].columns)}" for a in aliases if a in self.executor.datasets]
        return f"""Generate pandas code: {query}

Datasets: {chr(10).join(ds_info)}

Requirements:
- Store result in 'result' variable
- Use pandas/numpy only
- Return ONLY code

Example:
Query: "Average price"
Code: result = df['price'].mean()

Your code:"""

    def _extract_code(self, text: str) -> str:
        if "```python" in text:
            return text.split("```python")[1].split("```")[0].strip()
        elif "```" in text:
            return text.split("```")[1].split("```")[0].strip()
        return text.strip()


class VisualizeTool(BaseTool):
    def __init__(self, llm_client, executor: SafeCodeExecutor, retry_delay: float = 2.0, max_retries: int = 3):
        self.llm = llm_client
        self.executor = executor
        self.retry_delay = retry_delay
        self.max_retries = max_retries

    @property
    def name(self) -> str:
        return "visualize"

    @property
    def description(self) -> str:
        return "Generate and execute visualization code."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "dataset_aliases": {"type": "array", "items": {"type": "string"}},
                "chart_type": {"type": "string"}
            },
            "required": ["query", "dataset_aliases"]
        }

    def execute(self, query: str, dataset_aliases: list, chart_type: str = None) -> Dict[str, Any]:
        prompt = self._build_prompt(query, dataset_aliases, chart_type)

        for attempt in range(self.max_retries):
            try:
                response = self.llm.generate_content(prompt)
                code = self._extract_code(response.text)
                filepath = f"plot_{int(time.time())}.png"

                result = self.executor.execute_and_save_plot(code, filepath)
                if result["status"] == "success":
                    result["data"] = {"filepath": filepath, "chart_type": chart_type or "chart"}
                return result
            except Exception as e:
                if "429" in str(e).lower() or "rate limit" in str(e).lower():
                    if attempt < self.max_retries - 1:
                        wait = self.retry_delay * (2 ** attempt)
                        logger.warning(f"Rate limit. Retrying in {wait}s...")
                        time.sleep(wait)
                        continue
                return {"status": "error", "error_message": str(e)}

        return {"status": "error", "error_message": "Failed after retries"}

    def _build_prompt(self, query: str, aliases: list, chart_type: str = None) -> str:
        ds_info = [f"- {a}: {list(self.executor.datasets[a].columns)}" for a in aliases if a in self.executor.datasets]
        hint = f"\nChart type: {chart_type}" if chart_type else ""
        return f"""Generate matplotlib code: {query}

Datasets: {chr(10).join(ds_info)}{hint}

Requirements:
- Use matplotlib/seaborn
- Add title and labels
- Do NOT call plt.show()
- Return ONLY code

Your code:"""

    def _extract_code(self, text: str) -> str:
        if "```python" in text:
            return text.split("```python")[1].split("```")[0].strip()
        elif "```" in text:
            return text.split("```")[1].split("```")[0].strip()
        return text.strip()
