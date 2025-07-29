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
import pandas as pd
import json
import glob
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple

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
            
            # Use metadata values directly (more reliable than filename parsing)
            filename = os.path.basename(file_path)
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

def create_metric_chart(df: pd.DataFrame, metric: str, selected_configurations: List[Dict]) -> go.Figure:
    """Create a line chart for a specific metric."""
    
    # Filter data for the metric (excluding MRR for line plots)
    metric_df = df[(df['metric_name'] == metric) & (df['k_value'].notna())]
    
    # Filter by selected configurations
    if selected_configurations:
        config_filter = pd.Series([False] * len(metric_df))
        for config in selected_configurations:
            config_match = (
                (metric_df['rouge_threshold'] == config['rouge_threshold']) &
                (metric_df['max_tokens'] == config['max_tokens']) &
                (metric_df['overlap_tokens'] == config['overlap_tokens'])
            )
            config_filter = config_filter | config_match
        metric_df = metric_df[config_filter]
    
    if metric_df.empty:
        return go.Figure().add_annotation(text="No data available", showarrow=False)
    
    fig = go.Figure()
    
    # Create a line for each unique configuration with extended styling
    # Extended color palette for many configurations
    colors = (px.colors.qualitative.Set1 + 
              px.colors.qualitative.Set2 + 
              px.colors.qualitative.Set3 + 
              px.colors.qualitative.Pastel1 + 
              px.colors.qualitative.Pastel2)
    
    # Line style variations for better distinguishability
    line_styles = ['solid', 'dash', 'dot', 'dashdot']
    
    # Marker styles for additional variation
    marker_symbols = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up', 'triangle-down', 'star']
    
    unique_configs = metric_df[['rouge_threshold', 'max_tokens', 'overlap_tokens']].drop_duplicates()
    
    for i, (_, config) in enumerate(unique_configs.iterrows()):
        rouge_threshold = config['rouge_threshold']
        max_tokens = config['max_tokens']
        overlap_tokens = config['overlap_tokens']
        
        config_df = metric_df[
            (metric_df['rouge_threshold'] == rouge_threshold) &
            (metric_df['max_tokens'] == max_tokens) &
            (metric_df['overlap_tokens'] == overlap_tokens)
        ]
        
        if not config_df.empty:
            # Sort by k_value for proper line connection
            config_df = config_df.sort_values('k_value')
            
            # Create a descriptive label
            label = f'Rouge {rouge_threshold}, {max_tokens}tkn'
            if overlap_tokens > 0:
                label += f', overlap {overlap_tokens}'
            
            # Use cycling styles for better distinguishability with many configurations
            color = colors[i % len(colors)]
            line_style = line_styles[i % len(line_styles)]
            marker_symbol = marker_symbols[i % len(marker_symbols)]
            
            fig.add_trace(go.Scatter(
                x=config_df['k_value'],
                y=config_df['score'],
                mode='lines+markers',
                name=label,
                line=dict(
                    color=color, 
                    width=3, 
                    dash=line_style
                ),
                marker=dict(
                    size=8, 
                    symbol=marker_symbol,
                    color=color,
                    line=dict(width=2, color='white')
                ),
                hovertemplate=(
                    f'<b>{label}</b><br>'
                    'K: %{x}<br>'
                    f'{metric.title()}: %{{y:.3f}}<br>'
                    '<extra></extra>'
                )
            ))
    
    # Adaptive layout based on number of configurations
    num_configs = len(unique_configs)
    
    # Adjust height and legend position for many configurations
    if num_configs <= 4:
        height = 400
        legend_config = dict(
            orientation="v",
            yanchor="top",
            y=1,
            xanchor="left",
            x=1.02
        )
    elif num_configs <= 8:
        height = 450
        legend_config = dict(
            orientation="v",
            yanchor="top", 
            y=1,
            xanchor="left",
            x=1.02,
            font=dict(size=10)
        )
    else:
        height = 500
        legend_config = dict(
            orientation="h",
            yanchor="bottom",
            y=-0.3,
            xanchor="center",
            x=0.5,
            font=dict(size=9)
        )
    
    fig.update_layout(
        title=f'{metric.title()} @ K',
        xaxis_title='K Value',
        yaxis_title=f'{metric.title()} Score',
        hovermode='closest',
        showlegend=True,
        height=height,
        margin=dict(l=0, r=0, t=40, b=0 if num_configs <= 8 else 80),
        legend=legend_config
    )
    
    # Set x-axis to show only integer values
    fig.update_xaxes(tickmode='array', tickvals=[1, 3, 5, 10])
    
    return fig

def display_mrr_values(df: pd.DataFrame, selected_configurations: List[Dict]):
    """Display MRR values as cards below the charts."""
    
    mrr_df = df[(df['metric_name'] == 'mrr')]
    
    # Note: No secondary filtering needed here since df is already filtered by main()
    
    if mrr_df.empty:
        st.warning("No MRR data available for selected filters.")
        return
    
    st.subheader("📏 Mean Reciprocal Rank (MRR)")
    
    # Get unique configurations
    unique_configs = mrr_df[['rouge_threshold', 'max_tokens', 'overlap_tokens']].drop_duplicates()
    num_configs = len(unique_configs)
    
    # Create explicit layout that ensures all configurations are displayed
    config_list = list(unique_configs.iterrows())
    
    # For 4 configurations, use explicit 2x2 grid
    if num_configs == 4:
        # First row
        col1, col2 = st.columns(2)
        # Second row
        col3, col4 = st.columns(2)
        columns = [col1, col2, col3, col4]
    elif num_configs <= 2:
        columns = st.columns(num_configs)
    elif num_configs == 3:
        col1, col2 = st.columns(2)
        col3, _ = st.columns(2)  # Use underscore for unused column
        columns = [col1, col2, col3]
    elif num_configs <= 6:
        # Use 2 rows of 3 columns for 5-6 items
        col1, col2, col3 = st.columns(3)
        if num_configs > 3:
            col4, col5, col6 = st.columns(3)
            columns = [col1, col2, col3, col4, col5, col6][:num_configs]
        else:
            columns = [col1, col2, col3]
    elif num_configs <= 9:
        # Use 3 rows of 3 columns for 7-9 items
        col1, col2, col3 = st.columns(3)
        col4, col5, col6 = st.columns(3)
        col7, col8, col9 = st.columns(3)
        columns = [col1, col2, col3, col4, col5, col6, col7, col8, col9][:num_configs]
    else:
        # For many items, use multiple rows of 4 columns
        columns = []
        remaining = num_configs
        while remaining > 0:
            row_size = min(4, remaining)
            row_cols = st.columns(4)
            columns.extend(row_cols[:row_size])
            remaining -= row_size
    
    # Display each configuration
    for i, (_, config) in enumerate(config_list):
        rouge_threshold = config['rouge_threshold']
        max_tokens = config['max_tokens']
        overlap_tokens = config['overlap_tokens']
        
        config_mrr = mrr_df[
            (mrr_df['rouge_threshold'] == rouge_threshold) &
            (mrr_df['max_tokens'] == max_tokens) &
            (mrr_df['overlap_tokens'] == overlap_tokens)
        ]
        
        # Create a descriptive label
        label = f'Rouge {rouge_threshold}, {int(max_tokens)}tkn'
        if overlap_tokens > 0:
            label += f', overlap {int(overlap_tokens)}'
        
        if not config_mrr.empty and i < len(columns):
            mrr_score = config_mrr.iloc[0]['score']
            correct_retrievals = config_mrr.iloc[0]['correct_retrievals']
            total_questions = config_mrr.iloc[0]['total_questions']
            
            # Display in the appropriate column
            with columns[i]:
                st.metric(
                    label=label,
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
    
    # Configuration selection
    unique_configs = df[['rouge_threshold', 'max_tokens', 'overlap_tokens']].drop_duplicates()
    config_options = []
    config_labels = []
    
    for _, config in unique_configs.iterrows():
        config_dict = {
            'rouge_threshold': config['rouge_threshold'],
            'max_tokens': config['max_tokens'],
            'overlap_tokens': config['overlap_tokens']
        }
        config_options.append(config_dict)
        
        # Create descriptive label
        label = f'Rouge {config["rouge_threshold"]}, {config["max_tokens"]}tkn'
        if config['overlap_tokens'] > 0:
            label += f', overlap {config["overlap_tokens"]}'
        config_labels.append(label)
    
    # Multi-select for configurations
    selected_config_indices = st.sidebar.multiselect(
        "Configurations",
        options=list(range(len(config_options))),
        format_func=lambda x: config_labels[x],
        default=list(range(len(config_options))),
        help="Select which configurations to display"
    )
    
    if not selected_config_indices:
        st.warning("Please select at least one configuration.")
        return
    
    selected_configurations = [config_options[i] for i in selected_config_indices]
    
    # Display information about configuration count and readability
    num_selected = len(selected_configurations)
    if num_selected > 8:
        st.sidebar.warning(
            f"⚠️ {num_selected} configurations selected. "
            "Consider filtering to improve chart readability."
        )
    elif num_selected > 4:
        st.sidebar.info(
            f"ℹ️ {num_selected} configurations selected. "
            "Charts will use extended styling for clarity."
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
    
    # No additional validation needed since models are constant
    
    # Apply configuration filters
    config_filter = pd.Series([False] * len(df))
    for config in selected_configurations:
        config_match = (
            (df['rouge_threshold'] == config['rouge_threshold']) &
            (df['max_tokens'] == config['max_tokens']) &
            (df['overlap_tokens'] == config['overlap_tokens'])
        )
        config_filter = config_filter | config_match
    
    # Apply all filters
    filtered_df = df[
        config_filter &
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
        fig = create_metric_chart(filtered_df, selected_metrics[0], selected_configurations)
        st.plotly_chart(fig, use_container_width=True)
    elif len(selected_metrics) == 2:
        col1, col2 = st.columns(2)
        with col1:
            fig1 = create_metric_chart(filtered_df, selected_metrics[0], selected_configurations)
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = create_metric_chart(filtered_df, selected_metrics[1], selected_configurations)
            st.plotly_chart(fig2, use_container_width=True)
    else:
        # For 3 metrics, use 2+1 layout
        col1, col2 = st.columns(2)
        with col1:
            fig1 = create_metric_chart(filtered_df, selected_metrics[0], selected_configurations)
            st.plotly_chart(fig1, use_container_width=True)
        with col2:
            fig2 = create_metric_chart(filtered_df, selected_metrics[1], selected_configurations)
            st.plotly_chart(fig2, use_container_width=True)
        
        fig3 = create_metric_chart(filtered_df, selected_metrics[2], selected_configurations)
        st.plotly_chart(fig3, use_container_width=True)
    
    # Display MRR values
    display_mrr_values(filtered_df, selected_configurations)
    
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
            st.metric("Unique Configs", len(df[['rouge_threshold', 'max_tokens', 'overlap_tokens']].drop_duplicates()))
        
        # Configuration details
        st.markdown("### Detailed Configuration Summary")
        summary_df = pd.DataFrame.from_dict(metadata_info, orient='index')
        st.dataframe(summary_df, use_container_width=True)
        
        # Filtered data preview
        if len(filtered_df) > 0:
            st.markdown("### Filtered Data Preview")
            preview_cols = ['metric_name', 'k_value', 'score', 'rouge_threshold', 'max_tokens', 'overlap_tokens']
            st.dataframe(filtered_df[preview_cols].head(10), use_container_width=True)
        else:
            st.warning("No data matches the current filters.")

if __name__ == "__main__":
    main() 