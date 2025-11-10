# Global dataset storage (long-term memory)
_DATASET_STORE: Dict[str, pd.DataFrame] = {}

class LoadCSVTool(BaseTool):
    """Load a CSV file into the dataset store."""

    @property
    def name(self) -> str:
        return "load_csv"

    @property
    def description(self) -> str:
        return "Load a CSV file into memory with an alias for reference."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "filepath": {"type": "string", "description": "Path to CSV"},
                "alias": {"type": "string", "description": "Dataset name"}
            },
            "required": ["filepath", "alias"]
        }

    def execute(self, filepath: str, alias: str) -> Dict[str, Any]:
        try:
            df = pd.read_csv(filepath)
            _DATASET_STORE[alias] = df
            return {
                "status": "success",
                "result": f"Loaded '{filepath}' as '{alias}' with {len(df)} rows, {len(df.columns)} columns. Columns: {list(df.columns)}"
            }
        except Exception as e:
            return {"status": "error", "error_message": f"Failed to load: {str(e)}"}


class ListDatasetsTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_datasets"

    @property
    def description(self) -> str:
        return "List all loaded datasets."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {"type": "object", "properties": {}, "required": []}

    def execute(self) -> Dict[str, Any]:
        if not _DATASET_STORE:
            return {"status": "success", "result": "No datasets loaded."}

        summaries = [
            f"- '{a}': {len(df)} rows, {len(df.columns)} cols {list(df.columns)}"
            for a, df in _DATASET_STORE.items()
        ]
        return {"status": "success", "result": "Loaded datasets:\n" + "\n".join(summaries)}


class InspectDatasetTool(BaseTool):
    @property
    def name(self) -> str:
        return "inspect_dataset"

    @property
    def description(self) -> str:
        return "Get detailed info about a dataset."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {"alias": {"type": "string"}},
            "required": ["alias"]
        }

    def execute(self, alias: str) -> Dict[str, Any]:
        if alias not in _DATASET_STORE:
            return {"status": "error", "error_message": f"Dataset '{alias}' not found"}

        df = _DATASET_STORE[alias]
        info = [f"Dataset: {alias}", f"Shape: {df.shape[0]} rows × {df.shape[1]} cols", "\nColumns:"]

        for col in df.columns:
            nulls = df[col].isnull().sum()
            info.append(f"  - {col}: {df[col].dtype} ({nulls} nulls)")

        info.append("\nFirst 5 rows:")
        info.append(df.head().to_string())

        return {"status": "success", "result": "\n".join(info)}
