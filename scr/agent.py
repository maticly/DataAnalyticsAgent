logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataAnalyticsAgent:
    """
    ReAct agent for data analytics using Google's Gemini.

    Orchestrates tools using Think → Act → Observe loops to answer
    data analysis queries.
    """

    def __init__(
        self,
        gemini_model,
        max_iterations: int = 20,
        verbose: bool = True,
        retry_delay: float = 2.0,
        max_retries: int = 3
    ):
        """
        Initialize the agent.

        Args:
            gemini_model: Configured Gemini model instance
            max_iterations: Max ReAct iterations (default: 20)
            verbose: Print detailed logs (default: True)
            retry_delay: Seconds to wait between retries (default: 2.0)
            max_retries: Maximum retry attempts for 429 errors (default: 3)
        """
        self.llm = gemini_model
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.retry_delay = retry_delay
        self.max_retries = max_retries

        # Initialize memory
        self.memory = ConversationMemory()

        # Initialize executor (empty datasets initially)
        self.executor = SafeCodeExecutor({})

        # Initialize tools
        if 'df' in globals() and isinstance(globals()['df'], pd.DataFrame):
            _DATASET_STORE['df'] = globals()['df']

        self.tools: Dict[str, BaseTool] = {
            "list_datasets": ListDatasetsTool(),
            "inspect_dataset": InspectDatasetTool(),
            "analyze": AnalyzeTool(self.llm, self.executor),
            "visualize": VisualizeTool(self.llm, self.executor)
        }

        logger.info(f"Agent initialized with {len(self.tools)} tools")

    def run(self, user_query: str) -> Dict[str, Any]:
        """
        Execute ReAct loop to answer user query.

        Args:
            user_query: Natural language query

        Returns:
            Dictionary with status, answer, visualizations, etc.
        """
        iterations = 0
        visualizations = []
        conversation_history = []

        if self.verbose:
            print(f"\n{'='*80}")
            print(f"USER QUERY: {user_query}")
            print(f"{'='*80}")

        # Main ReAct loop
        while iterations < self.max_iterations:
            iterations += 1

            # Step 1: Build context prompt
            try:
                agent_prompt = self._build_context_prompt(
                    user_query,
                    current_iteration=iterations
                )
            except Exception as e:
                logger.error(f"Failed to build prompt: {e}")
                return {
                    "status": "error",
                    "error_message": f"Prompt error: {str(e)}",
                    "iterations": iterations
                }

            # Step 2: Get LLM decision with retry logic
            try:
                llm_response = self._call_llm_with_retry(agent_prompt)
            except Exception as e:
                logger.error(f"LLM call failed after retries: {e}")
                return {
                    "status": "error",
                    "error_message": f"LLM error: {str(e)}",
                    "iterations": iterations
                }

            # Step 3: Parse response
            thought = llm_response.get("thought", "")
            action = llm_response.get("action", "")
            parameters = llm_response.get("parameters", {})

            logger.info(f"===== ITERATION {iterations} === [USER QUERY]: {user_query}")
            logger.info(f"THOUGHT: {thought}")
            logger.info(f"ACTION: {action}")
            logger.info(f"PARAMETERS: {parameters}")

            if self.verbose:
                self._print_step(iterations, thought, action, parameters)

            # Step 4: Check if done
            if action == "DONE":
                final_answer = parameters.get("answer", "")

                if not final_answer:
                    return {
                        "status": "error",
                        "error_message": "Agent finished without answer",
                        "iterations": iterations
                    }

                if self.verbose:
                    print(f"\n{'='*80}")
                    print(f"FINAL ANSWER: {final_answer}")
                    print(f"{'_'*80}")

                return {
                    "status": "success",
                    "answer": final_answer,
                    "visualizations": visualizations,
                    "iterations": iterations,
                    "conversation_history": conversation_history
                }

            # Step 5: Execute tool
            result = self._execute_tool(action, parameters)

            logger.info(f"RESULT: {self._summarize_result(result)}")

            if self.verbose:
                self._print_result(result)

            # Step 6: Track visualizations
            if action == "visualize" and result.get("status") == "success":
                data = result.get("data", {})
                if isinstance(data, dict) and "filepath" in data:
                    visualizations.append({
                        "filepath": data["filepath"],
                        "chart_type": data.get("chart_type", "chart")
                    })

            # Step 7: Update executor datasets
            self._update_executor_datasets()

            # Step 8: Add to memory
            result_summary = self._summarize_result(result)
            self.memory.add_turn(
                query=user_query,
                thought=thought,
                action=action,
                action_params=parameters,
                result=result_summary
            )

            # Step 9: Track history
            conversation_history.append({
                "iteration": iterations,
                "thought": thought,
                "action": action,
                "parameters": parameters,
                "result": result
            })

        # Max iterations reached
        logger.warning(f"Max iterations ({self.max_iterations}) reached")
        return {
            "status": "error",
            "error_message": f"Did not complete within {self.max_iterations} iterations",
            "iterations": iterations,
            "conversation_history": conversation_history
        }

    def _call_llm_with_retry(self, prompt: str) -> Dict[str, Any]:
        """
        Call LLM with exponential backoff retry logic for 429 errors.

        Args:
            prompt: Complete prompt with context

        Returns:
            Parsed JSON response

        Raises:
            RuntimeError: If all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                return self._call_llm(prompt)
            except Exception as e:
                error_msg = str(e).lower()

                # Check if it's a 429 error
                if "429" in error_msg or "quota" in error_msg or "rate limit" in error_msg:
                    if attempt < self.max_retries - 1:
                        # Exponential backoff: 2s, 4s, 8s, etc.
                        wait_time = self.retry_delay * (2 ** attempt)
                        logger.warning(f"Rate limit hit (429). Retrying in {wait_time}s... (attempt {attempt + 1}/{self.max_retries})")

                        if self.verbose:
                            print(f"⏳ Rate limit reached. Waiting {wait_time}s before retry...")

                        time.sleep(wait_time)
                        continue
                    else:
                        raise RuntimeError(f"Rate limit exceeded after {self.max_retries} attempts. Please wait and try again.")
                else:
                    # Non-429 error, don't retry
                    raise e

        raise RuntimeError("Failed to call LLM after all retries")

    def _build_context_prompt(
        self,
        user_query: str,
        current_iteration: int = 1
    ) -> str:
        """Build complete prompt with context."""
        # Get base prompt
        base_prompt = build_agent_prompt(
            tools=list(self.tools.values()),
            datasets=_DATASET_STORE,
            max_iterations=self.max_iterations
        )

        # Add recent context
        recent_context = self.memory.get_recent_context(last_n=3)

        # Build final prompt
        full_prompt = f"""{base_prompt}

{recent_context}

## Current Iteration: {current_iteration} / {self.max_iterations}

## Current User Query

{user_query}

Remember: Respond with valid JSON only!
"""
        return full_prompt

    def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """Call Gemini to decide next action."""
        try:
            # Call Gemini
            response = self.llm.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.1,
                    candidate_count=1,
                )
            )

            content = response.text

            # Parse JSON
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown
                if "```json" in content:
                    start = content.find("```json") + 7
                    end = content.find("```", start)
                    if end != -1:
                        json_str = content[start:end].strip()
                        parsed = json.loads(json_str)
                    else:
                        raise RuntimeError(f"Invalid JSON: {content[:200]}")
                else:
                    raise RuntimeError(f"Failed to parse: {content[:200]}")

            # Validate required fields
            if "thought" not in parsed or "action" not in parsed:
                raise RuntimeError(f"Missing fields: {parsed}")

            # Ensure parameters exists
            if "parameters" not in parsed:
                parsed["parameters"] = {}

            # Handle DONE action
            if parsed["action"] == "DONE":
                if "answer" not in parsed["parameters"]:
                    if "answer" in parsed:
                        parsed["parameters"]["answer"] = parsed["answer"]

            return parsed

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise RuntimeError(f"LLM error: {str(e)}")

    def _execute_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a tool with parameters."""
        if tool_name not in self.tools:
            return {
                "status": "error",
                "error_message": f"Tool '{tool_name}' not found"
            }

        tool = self.tools[tool_name]

        try:
            result = tool.execute(**parameters)
            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return {
                "status": "error",
                "error_message": f"Tool error: {str(e)}"
            }

    def _update_executor_datasets(self):
        """Update executor with current datasets."""
        self.executor.update_datasets(_DATASET_STORE)

    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Summarize result for memory."""
        if result.get("status") == "error":
            return f"Error: {result.get('error_message', 'Unknown')}"

        result_str = str(result.get("result", ""))
        if len(result_str) > 500:
            return result_str[:500] + "..."
        return result_str

    def _print_step(self, iteration, thought, action, parameters):
        """Print current step if verbose."""
        if not self.verbose:
            return

        print(f"\n{'='*80}")
        print(f"ITERATION {iteration}")
        print(f"{'='*80}")
        print(f"THOUGHT: {thought}")
        print(f"ACTION: {action}")

        if parameters:
            print("PARAMETERS:")
            for k, v in parameters.items():
                v_str = str(v)
                if len(v_str) > 100:
                    v_str = v_str[:100] + "..."
                print(f"  {k}: {v_str}")

    def _print_result(self, result):
        """Print result if verbose."""
        if not self.verbose:
            return

        print(f"\nRESULT:")
        status = result.get("status", "unknown")

        if status == "success":
            result_str = str(result.get("result", ""))
            if len(result_str) > 500:
                result_str = result_str[:500] + "..."
            print(f"  Status: success")
            print(f"  Output: {result_str}")
        else:
            print(f"  Status: error")
            print(f"  Error: {result.get('error_message', 'Unknown')}")

    def clear_memory(self):
        """Clear conversation memory."""
        self.memory.clear()
        logger.info("Memory cleared")

print("✅ DataAnalyticsAgent core defined successfully!")

# Instantiate the agent again after updating the class definition
agent = DataAnalyticsAgent(
    gemini_model=model,
    max_iterations=20,
    verbose=True
)

print("✅ Agent ready!")
