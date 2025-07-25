# Interactive Evaluation Results Dashboard

*Date: 2025-07-24*
*Type: New Feature Prototyping*

## Objective
Build an interactive web-based visualization dashboard for exploring aggregated evaluation results with multi-select filtering and dynamic charting capabilities, replacing static seaborn plots.

## Results
• **Streamlit + Plotly Dashboard** - Complete interactive web interface with multi-select metadata filtering
• **Dynamic Line Charts** - Precision, recall, ndcg metrics vs K-values with toggle-able rouge thresholds  
• **MRR Integration** - Mean Reciprocal Rank values displayed as metric cards beneath visualizations
• **Comprehensive Metadata Exposure** - All evaluation parameters (QA models, embedding models, chunking config) available as filters

## Implementation
- **Main Dashboard** (`evaluation/scripts/interactive_visualization.py`)
- **Data Loading** - Automatic discovery and parsing of aggregated results JSON files
- **Multi-Select Filtering** - Rouge thresholds, QA models, embedding models, chunking parameters
- **Interactive Charts** - Plotly line plots with hover tooltips showing complete configuration details
- **Responsive Layout** - Adapts chart arrangement based on selected metrics (1, 2, or 3 charts)

## Impact
- **Enhanced Analysis** - Researchers can interactively explore evaluation results across all experimental dimensions
- **Configuration Comparison** - Easy toggle between different models, rouge thresholds, and chunking parameters
- **Data Transparency** - Comprehensive metadata display ensures full experimental context visibility
- **Scalable Design** - Ready for expansion as more evaluation configurations are added

## Key Features
- Web-based interface accessible at `http://localhost:8501`
- Real-time filtering with validation to prevent empty result sets
- Detailed hover information showing QA model, embedding model, and chunking configuration
- Data summary section with configuration overview and filtered data preview
- Single-path data loading for reliable file discovery

## Technical Architecture
Streamlit provides the web framework, Plotly handles interactive charting, pandas manages data manipulation. The system loads all `aggregated_results_*.json` files from `evaluation/data/results/` and structures them for filtering and visualization.

## Usage
```bash
cd evaluation/scripts
streamlit run interactive_visualization.py
```

Dashboard serves researchers analyzing RAG retrieval performance across different experimental configurations, enabling data-driven optimization decisions. 