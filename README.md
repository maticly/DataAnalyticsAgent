# 🤖 ReAct Data Analytics Agent

> An intelligent data analytics agent powered by Google Gemini and the ReAct (Reasoning + Acting) framework

![Demo](images/demo.gif)

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/YOUR_USERNAME/react-data-agent/blob/main/notebooks/complete_agent.ipynb)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## ✨ Features

- 🧠 **ReAct Reasoning**: Systematic think-act-observe loops for robust analysis
- 💾 **Dual Memory System**: Short-term conversation + long-term dataset storage
- 🛠️ **5 Powerful Tools**: Load, inspect, analyze, and visualize data
- 🔄 **Auto Retry Logic**: Handles rate limits with exponential backoff
- 📊 **LLM-Generated Code**: Gemini creates pandas/matplotlib code on the fly
- 🎨 **Interactive UI**: Chat-like interface in Google Colab
- 🔒 **Safe Execution**: Sandboxed code runner prevents system access

## 🚀 Quick Start

### Option 1: Google Colab (Recommended)
1. Click the "Open in Colab" badge above
2. Add your Gemini API key
3. Run all cells
4. Start analyzing data!

### Option 2: Local Installation
```bash
git clone https://github.com/YOUR_USERNAME/react-data-agent.git
cd react-data-agent
pip install -r requirements.txt
```

## 💡 Usage Examples

### Load and Analyze Data
```python
from src.agent import DataAnalyticsAgent
import google.generativeai as genai

# Initialize
genai.configure(api_key="YOUR_API_KEY")
model = genai.GenerativeModel("gemini-1.5-pro")
agent = DataAnalyticsAgent(model)

# Analyze
result = agent.run("Load insurance.csv and show me average premium by region")
print(result["answer"])
```

### Interactive Interface
```python
from src.interface import setup_datasets_with_ui, ColabAgentInterface

# Load data with UI
setup_datasets_with_ui()

# Start chat interface
interface = ColabAgentInterface(agent)
interface.display()
```

## 🏗️ Architecture
User Query
↓
┌─────────────────────┐
│  DataAnalyticsAgent │
│   (ReAct Loop)      │
└─────────────────────┘
↓
┌─────────────────────┐
│  Reasoning (LLM)    │ ← Google Gemini
│  • Think           │
│  • Plan            │
│  • Decide          │
└─────────────────────┘
↓
┌─────────────────────┐
│  Tool Selection     │
│  • load_csv         │
│  • analyze          │
│  • visualize        │
│  • inspect          │
└─────────────────────┘
↓
┌─────────────────────┐
│  Code Executor      │ ← Safe sandbox
│  • Run pandas       │
│  • Generate plots   │
└─────────────────────┘
↓
Result → Memory → Next Iteration

## 📊 Example Queries

- "Load sales.csv and show me total revenue by product"
- "What are the top 5 customers by purchase frequency?"
- "Create a bar chart of monthly sales trends"
- "Which regions have the highest average order value?"
- "Show me correlation between age and insurance premium"

## 🧠 How It Works

The agent uses the **ReAct (Reasoning + Acting)** pattern:

1. **THINK**: "User wants sales trends. I need to check if data is loaded."
2. **ACT**: Execute `list_datasets()` tool
3. **OBSERVE**: "No datasets loaded yet"
4. **THINK**: "I need to load the data first"
5. **ACT**: Execute `load_csv(filepath="sales.csv")`
6. **OBSERVE**: "Data loaded successfully with 1000 rows"
7. **THINK**: "Now I can analyze trends"
8. **ACT**: Execute `analyze(query="calculate monthly sales")`
9. **OBSERVE**: "Analysis complete: [results]"
10. **THINK**: "I have the answer"
11. **ACT**: `DONE` with final answer

## 🛠️ Components

### Core Agent (`src/agent.py`)
- Orchestrates ReAct loop
- Manages iterations and memory
- Handles retry logic

### Tools (`src/tools/`)
- **LoadCSVTool**: Load datasets into memory
- **ListDatasetsTool**: View available data
- **InspectDatasetTool**: Examine structure
- **AnalyzeTool**: Generate pandas code
- **VisualizeTool**: Create charts

### Memory (`src/memory.py`)
- **Short-term**: Recent conversation (50 turns)
- **Long-term**: Loaded datasets (persistent)

### Executor (`src/executor.py`)
- Safe code execution
- Sandboxed environment
- Prevents file system access

## 🔧 Configuration
```python
agent = DataAnalyticsAgent(
    gemini_model=model,
    max_iterations=20,      # Max reasoning steps
    verbose=True,           # Print reasoning
    retry_delay=2.0,        # Rate limit backoff
    max_retries=3           # Max retry attempts
)
```

## 📈 Performance

- **Average query time**: 10-30 seconds
- **Typical iterations**: 3-8 steps
- **Rate limit handling**: Automatic retry with backoff
- **Memory usage**: ~50MB per 1M row dataset

## 🐛 Troubleshooting

### Rate Limit (429) Errors
The agent automatically handles rate limits with exponential backoff. If you still encounter issues:
- Increase `retry_delay` (default: 2.0s)
- Increase `max_retries` (default: 3)
- Wait 60 seconds between complex queries

### "Dataset not found" Errors
Always load data first:
```python
agent.run("Load mydata.csv as 'data'")
agent.run("Now analyze the data")  # Works!
```

### Code Generation Issues
If the LLM generates incorrect code:
- Use `inspect_dataset` to show column names
- Be specific in your query
- Try rephrasing the question


## 📄 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

- [ReAct Paper](https://arxiv.org/abs/2210.03629) by Yao et al.
- Google Gemini API
- Anthropic for Claude (inspiration)
