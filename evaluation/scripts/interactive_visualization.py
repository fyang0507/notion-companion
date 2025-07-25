#!/usr/bin/env python3
"""
Interactive Visualization Dashboard for Evaluation Results

This Streamlit app provides an interactive interface to visualize aggregated 
evaluation results with multi-select filtering and Plotly line charts.

Usage:
    streamlit run evaluation/scripts/interactive_visualization.py
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import json
import glob
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple
import re

# Page configuration
st.set_page_config(
    page_title="Evaluation Results Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

@st.cache_data
def load_aggregated_results() -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Load all aggregated results JSON files and return structured data."""
    
    # Get results directory relative to script location
    results_dir = Path(__file__).parent.parent / "data" / "results"
    pattern = str(results_dir / "aggregated_results_*.json")
    result_files = glob.glob(pattern)
    
    if not result_files:
        st.error(f"No aggregated results files found in {results_dir}")
        return pd.DataFrame(), {}
    
    all_data = []
    metadata_info = {}
    
    for file_path in result_files:
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Extract metadata
            metadata = data['metadata']
            
            # Parse filename to extract configuration
            filename = os.path.basename(file_path)
            config_match = re.search(r'rouge(\d+)_maxtkn(\d+)_overlap(\d+)', filename)
            if config_match:
                rouge_threshold = float(f"0.{config_match.group(1)}")
                max_tokens = int(config_match.group(2))
                overlap_tokens = int(config_match.group(3))
            else:
                rouge_threshold = metadata.get('rouge_threshold', 0.0)
                max_tokens = metadata.get('chunking_config', {}).get('max_tokens', 1000)
                overlap_tokens = metadata.get('chunking_config', {}).get('overlap_tokens', 0)
            
            # Process results
            results = data['results']
            
            for metric_key, metric_data in results.items():
                if metric_key == 'mrr':
                    # Special handling for MRR (no k_value)
                    row = {
                        'metric_name': 'mrr',
                        'k_value': None,
                        'score': metric_data['score'],
                        'rouge_threshold': rouge_threshold,
                        'max_tokens': max_tokens,
                        'overlap_tokens': overlap_tokens,
                        'embeddings_model': metadata.get('embeddings_config', {}).get('openai', {}).get('model', 'unknown'),
                        'qa_model': metadata.get('qa_metadata', {}).get('model', 'unknown'),
                        'total_questions': metric_data['total_questions'],
                        'correct_retrievals': metric_data['correct_retrievals'],
                        'filename': filename,
                        'timestamp': metadata['timestamp']
                    }
                    all_data.append(row)
                else:
                    # Handle precision, recall, ndcg metrics
                    row = {
                        'metric_name': metric_data['metric_name'].split('_at_')[0],
                        'k_value': metric_data['k_value'],
                        'score': metric_data['score'],
                        'rouge_threshold': rouge_threshold,
                        'max_tokens': max_tokens,
                        'overlap_tokens': overlap_tokens,
                        'embeddings_model': metadata.get('embeddings_config', {}).get('openai', {}).get('model', 'unknown'),
                        'qa_model': metadata.get('qa_metadata', {}).get('model', 'unknown'),
                        'total_questions': metric_data['total_questions'],
                        'correct_retrievals': metric_data['correct_retrievals'],
                        'filename': filename,
                        'timestamp': metadata['timestamp']
                    }
                    all_data.append(row)
            
            # Store metadata info
            metadata_info[filename] = {
                'rouge_threshold': rouge_threshold,
                'max_tokens': max_tokens,
                'overlap_tokens': overlap_tokens,
                'embeddings_model': metadata.get('embeddings_config', {}).get('openai', {}).get('model', 'unknown'),
                'qa_model': metadata.get('qa_metadata', {}).get('model', 'unknown'),
                'timestamp': metadata['timestamp']
            }
            
        except Exception as e:
            st.error(f"Error loading {file_path}: {str(e)}")
            continue
    
    df = pd.DataFrame(all_data)
    return df, metadata_info

def create_metric_chart(df: pd.DataFrame, metric: str, selected_rouge_thresholds: List[float]) -> go.Figure:
    """Create a line chart for a specific metric."""
    
    # Filter data for the metric (excluding MRR for line plots)
    metric_df = df[(df['metric_name'] == metric) & (df['k_value'].notna())]
    metric_df = metric_df[metric_df['rouge_threshold'].isin(selected_rouge_thresholds)]
    
    if metric_df.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False)
    
    fig = go.Figure()
    
    # Create a line for each rouge threshold
    colors = px.colors.qualitative.Set1
    for i, rouge_threshold in enumerate(sorted(selected_rouge_thresholds)):
        threshold_df = metric_df[metric_df['rouge_threshold'] == rouge_threshold]
        
        if not threshold_df.empty:
            # Sort by k_value for proper line connection
            threshold_df = threshold_df.sort_values('k_value')
            
            fig.add_trace(go.Scatter(
                x=threshold_df['k_value'],
                y=threshold_df['score'],
                mode='lines+markers',
                name=f'Rouge {rouge_threshold}',
                line=dict(color=colors[i % len(colors)], width=3),
                marker=dict(size=8),
                hovertemplate=(
                    f'<b>Rouge Threshold: {rouge_threshold}</b><br>'
                    'K: %{x}<br>'
                    f'{metric.title()}: %{{y:.3f}}<br>'
                    f'QA Model: {threshold_df.iloc[0]["qa_model"]}<br>'
                    f'Embedding Model: {threshold_df.iloc[0]["embeddings_model"]}<br>'
                    f'Max Tokens: {threshold_df.iloc[0]["max_tokens"]}<br>'
                    '<extra></extra>'
                )
            ))
    
    fig.update_layout(
        title=f'{metric.title()} @ K',
        xaxis_title='K Value',
        yaxis_title=f'{metric.title()} Score',
        hovermode='closest',
        showlegend=True,
        height=400,
        margin=dict(l=0, r=0, t=40, b=0)
    )
    
    # Set x-axis to show only integer values
    fig.update_xaxes(tickmode='array', tickvals=[1, 3, 5, 10])
    
    return fig

def display_mrr_values(df: pd.DataFrame, selected_rouge_thresholds: List[float]):
    """Display MRR values as cards below the charts."""
    
    mrr_df = df[(df['metric_name'] == 'mrr')]
    mrr_df = mrr_df[mrr_df['rouge_threshold'].isin(selected_rouge_thresholds)]
    
    if mrr_df.empty:
        st.warning("No MRR data available for selected filters.")
        return
    
    st.subheader("📏 Mean Reciprocal Rank (MRR)")
    
    # Create columns for MRR values
    cols = st.columns(len(selected_rouge_thresholds))
    
    for i, rouge_threshold in enumerate(sorted(selected_rouge_thresholds)):
        threshold_mrr = mrr_df[mrr_df['rouge_threshold'] == rouge_threshold]
        
        if not threshold_mrr.empty:
            mrr_score = threshold_mrr.iloc[0]['score']
            correct_retrievals = threshold_mrr.iloc[0]['correct_retrievals']
            total_questions = threshold_mrr.iloc[0]['total_questions']
            
            with cols[i]:
                st.metric(
                    label=f"Rouge {rouge_threshold}",
                    value=f"{mrr_score:.3f}",
                    help=f"Correct retrievals: {correct_retrievals}/{total_questions}"
                )

def main():
    """Main Streamlit application."""
    
    st.title("📊 Evaluation Results Dashboard")
    st.markdown("Interactive visualization of retrieval evaluation metrics")
    
    # Load data
    with st.spinner("Loading evaluation results..."):
        df, metadata_info = load_aggregated_results()
    
    if df.empty:
        st.error("No data loaded. Please check your results files.")
        return
    
    # Sidebar for filtering
    st.sidebar.header("🔍 Filters")
    
    # Rouge threshold multi-select
    available_rouge_thresholds = sorted(df['rouge_threshold'].unique())
    selected_rouge_thresholds = st.sidebar.multiselect(
        "Rouge Thresholds",
        options=available_rouge_thresholds,
        default=available_rouge_thresholds,
        help="Select which rouge thresholds to display"
    )
    
    if not selected_rouge_thresholds:
        st.warning("Please select at least one rouge threshold.")
        return
    
    # Model configuration filters
    st.sidebar.header("🤖 Model Configuration")
    
    # QA Model selection
    available_qa_models = sorted(df['qa_model'].unique())
    selected_qa_models = st.sidebar.multiselect(
        "QA Models",
        options=available_qa_models,
        default=available_qa_models,
        help="Select which QA models to include"
    )
    
    # Embedding Model selection
    available_embedding_models = sorted(df['embeddings_model'].unique())
    selected_embedding_models = st.sidebar.multiselect(
        "Embedding Models",
        options=available_embedding_models,
        default=available_embedding_models,
        help="Select which embedding models to include"
    )
    
    # Chunking configuration filters
    with st.sidebar.expander("⚙️ Chunking Configuration"):
        available_max_tokens = sorted(df['max_tokens'].unique())
        selected_max_tokens = st.multiselect(
            "Max Tokens",
            options=available_max_tokens,
            default=available_max_tokens,
            help="Filter by chunking max tokens"
        )
        
        available_overlap_tokens = sorted(df['overlap_tokens'].unique())
        selected_overlap_tokens = st.multiselect(
            "Overlap Tokens",
            options=available_overlap_tokens,
            default=available_overlap_tokens,
            help="Filter by chunking overlap tokens"
        )
    
    # Validate all filter selections
    if not selected_qa_models:
        st.warning("Please select at least one QA model.")
        return
        
    if not selected_embedding_models:
        st.warning("Please select at least one embedding model.")
        return
    
    # Apply all filters
    filtered_df = df[
        (df['rouge_threshold'].isin(selected_rouge_thresholds)) &
        (df['qa_model'].isin(selected_qa_models)) &
        (df['embeddings_model'].isin(selected_embedding_models)) &
        (df['max_tokens'].isin(selected_max_tokens)) &
        (df['overlap_tokens'].isin(selected_overlap_tokens))
    ]
    
    # Metrics selection
    st.sidebar.header("📈 Metrics to Display")
    available_metrics = ['precision', 'recall', 'ndcg']
    selected_metrics = st.sidebar.multiselect(
        "Select Metrics",
        options=available_metrics,
        default=available_metrics,
        help="Choose which metrics to visualize"
    )
    
    # Main content area
    if not selected_metrics:
        st.warning("Please select at least one metric to display.")
        return
    
    # Display charts
    st.header("📈 Metric Performance vs K Values")
    
    # Create charts in columns
    if len(selected_metrics) == 1:
        fig = create_metric_chart(filtered_df, selected_metrics[0], selected_rouge_thresholds)
        st.plotly_chart(fig, use_container_width=True)
    elif len(selected_metrics) == 2:
        col1, col2 = st.columns(2)
        with col1:
            fig1 = create_metric_chart(filtered_df, selected_metrics[0], selected_rouge_thresholds)
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = create_metric_chart(filtered_df, selected_metrics[1], selected_rouge_thresholds)
            st.plotly_chart(fig2, use_container_width=True)
    else:
        # For 3 metrics, use 2+1 layout
        col1, col2 = st.columns(2)
        with col1:
            fig1 = create_metric_chart(filtered_df, selected_metrics[0], selected_rouge_thresholds)
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = create_metric_chart(filtered_df, selected_metrics[1], selected_rouge_thresholds)
            st.plotly_chart(fig2, use_container_width=True)
        
        fig3 = create_metric_chart(filtered_df, selected_metrics[2], selected_rouge_thresholds)
        st.plotly_chart(fig3, use_container_width=True)
    
    # Display MRR values
    display_mrr_values(filtered_df, selected_rouge_thresholds)
    
    # Data summary
    with st.expander("📊 Data Summary"):
        st.markdown("### Configuration Overview")
        
        # Create summary metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Data Points", len(filtered_df))
        with col2:
            st.metric("Files Loaded", len(metadata_info))
        with col3:
            st.metric("Rouge Thresholds", len(df['rouge_threshold'].unique()))
        with col4:
            st.metric("Unique Configs", len(df[['rouge_threshold', 'max_tokens', 'overlap_tokens', 'qa_model', 'embeddings_model']].drop_duplicates()))
        
        # Model information
        st.markdown("### Model Configuration")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**QA Models:**")
            for model in sorted(df['qa_model'].unique()):
                count = len(df[df['qa_model'] == model])
                st.markdown(f"- {model} ({count} data points)")
        
        with col2:
            st.markdown("**Embedding Models:**")
            for model in sorted(df['embeddings_model'].unique()):
                count = len(df[df['embeddings_model'] == model])
                st.markdown(f"- {model} ({count} data points)")
        
        # Configuration details
        st.markdown("### Detailed Configuration Summary")
        summary_df = pd.DataFrame.from_dict(metadata_info, orient='index')
        st.dataframe(summary_df, use_container_width=True)
        
        # Filtered data preview
        if len(filtered_df) > 0:
            st.markdown("### Filtered Data Preview")
            preview_cols = ['metric_name', 'k_value', 'score', 'rouge_threshold', 'qa_model', 'embeddings_model']
            st.dataframe(filtered_df[preview_cols].head(10), use_container_width=True)
        else:
            st.warning("No data matches the current filters.")

if __name__ == "__main__":
    main() 