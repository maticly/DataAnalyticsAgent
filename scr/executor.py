class SafeCodeExecutor:
    """Execute pandas code."""

    def __init__(self, datasets: Dict[str, pd.DataFrame]):
        self.datasets = datasets.copy()

    def update_datasets(self, datasets: Dict[str, pd.DataFrame]):
        self.datasets = datasets.copy()

    def execute(self, code: str, return_variable: str = "result") -> Dict[str, Any]:
        safe_globals = {
            "pd": pd, "np": np, "plt": plt, "sns": sns,
            "__builtins__": __builtins__,
        }

        for alias, df in self.datasets.items():
            safe_globals[alias] = df

        old_stdout = sys.stdout
        sys.stdout = captured = io.StringIO()

        try:
            exec(code, safe_globals)
            sys.stdout = old_stdout

            result = safe_globals.get(return_variable)
            result_str = result.to_string() if isinstance(result, (pd.DataFrame, pd.Series)) else str(result)

            return {
                "status": "success",
                "result": result_str,
                "stdout": captured.getvalue()
            }
        except Exception as e:
            sys.stdout = old_stdout
            return {
                "status": "error",
                "error_message": f"Execution error: {str(e)}",
                "stdout": captured.getvalue()
            }

    def execute_and_save_plot(self, code: str, filepath: str = "plot.png") -> Dict[str, Any]:
        safe_globals = {
            "pd": pd, "np": np, "plt": plt, "sns": sns,
            "__builtins__": __builtins__,
        }

        for alias, df in self.datasets.items():
            safe_globals[alias] = df

        try:
            exec(code, safe_globals)
            plt.savefig(filepath, dpi=100, bbox_inches='tight')
            plt.close()
            return {"status": "success", "filepath": filepath}
        except Exception as e:
            plt.close()
            return {"status": "error", "error_message": f"Plot failed: {str(e)}"}

print("✅ SafeCodeExecutor defined")
