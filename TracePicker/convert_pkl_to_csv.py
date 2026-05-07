#!/usr/bin/env python3
"""
Convert pkl files to CSV format
This script converts traces.pkl, spanLabels.pkl, and nodes.pkl to CSV files
"""

import pickle
import pandas as pd
import json
import sys
import os
from pathlib import Path

# Add the current directory to the Python path so we can import entity
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def convert_traces_pkl(pkl_file_path, output_csv_path):
    """Convert traces.pkl to CSV format"""
    print(f"Converting {pkl_file_path} to {output_csv_path}")
    
    try:
        with open(pkl_file_path, 'rb') as f:
            traces = pickle.load(f)
        
        trace_data = []
        span_data = []
        
        for trace in traces:
            # Extract trace-level information
            trace_info = {
                'traceID': trace.traceID,
                'span_count': len(trace.spans),
                'isError': getattr(trace, 'isError', False),
                'abnormal': getattr(trace, 'abnormal', False)
            }
            trace_data.append(trace_info)
            
            # Extract span-level information
            for span in trace.spans:
                span_info = {
                    'traceID': span.traceId,
                    'spanId': span.spanId,
                    'parentSpanId': span.parentSpanId,
                    'startTime': span.startTime,
                    'duration': span.duration,
                    'statusCode': span.statusCode,
                    'service': span.service,
                    'operation': span.operation,
                    'instance': span.instance
                }
                span_data.append(span_info)
        
        # Save trace-level data
        trace_df = pd.DataFrame(trace_data)
        trace_csv_path = output_csv_path.replace('.csv', '_traces.csv')
        trace_df.to_csv(trace_csv_path, index=False)
        print(f"Saved trace data to {trace_csv_path}")
        
        # Save span-level data
        span_df = pd.DataFrame(span_data)
        span_csv_path = output_csv_path.replace('.csv', '_spans.csv')
        span_df.to_csv(span_csv_path, index=False)
        print(f"Saved span data to {span_csv_path}")
        
        print(f"Total traces: {len(trace_data)}")
        print(f"Total spans: {len(span_data)}")
        
    except Exception as e:
        print(f"Error converting traces.pkl: {e}")
        import traceback
        traceback.print_exc()

def convert_span_labels_pkl(pkl_file_path, output_csv_path):
    """Convert spanLabels.pkl to CSV format"""
    print(f"Converting {pkl_file_path} to {output_csv_path}")
    
    try:
        with open(pkl_file_path, 'rb') as f:
            span_labels = pickle.load(f)
        
        # Convert to DataFrame
        if isinstance(span_labels, dict):
            # If it's a dictionary, convert to list of records
            data = []
            for key, value in span_labels.items():
                data.append({'key': key, 'value': value})
            df = pd.DataFrame(data)
        elif isinstance(span_labels, list):
            # If it's a list, convert directly
            if span_labels and isinstance(span_labels[0], dict):
                df = pd.DataFrame(span_labels)
            else:
                df = pd.DataFrame({'span_label': span_labels})
        else:
            # For other types, try to convert to DataFrame
            df = pd.DataFrame({'data': [str(span_labels)]})
        
        df.to_csv(output_csv_path, index=False)
        print(f"Saved to {output_csv_path}")
        print(f"Shape: {df.shape}")
        
    except Exception as e:
        print(f"Error converting spanLabels.pkl: {e}")
        import traceback
        traceback.print_exc()

def convert_nodes_pkl(pkl_file_path, output_csv_path):
    """Convert nodes.pkl to CSV format"""
    print(f"Converting {pkl_file_path} to {output_csv_path}")
    
    try:
        with open(pkl_file_path, 'rb') as f:
            nodes = pickle.load(f)
        
        # Convert to DataFrame
        if isinstance(nodes, dict):
            # If it's a dictionary, convert to list of records
            data = []
            for key, value in nodes.items():
                if isinstance(value, (list, tuple)):
                    # If value is a list/tuple, create separate columns
                    row = {'key': key}
                    for i, v in enumerate(value):
                        row[f'value_{i}'] = v
                    data.append(row)
                else:
                    data.append({'key': key, 'value': value})
            df = pd.DataFrame(data)
        elif isinstance(nodes, list):
            # If it's a list, convert directly
            if nodes and isinstance(nodes[0], dict):
                df = pd.DataFrame(nodes)
            else:
                df = pd.DataFrame({'node': nodes})
        else:
            # For other types, try to convert to DataFrame
            df = pd.DataFrame({'data': [str(nodes)]})
        
        df.to_csv(output_csv_path, index=False)
        print(f"Saved to {output_csv_path}")
        print(f"Shape: {df.shape}")
        
    except Exception as e:
        print(f"Error converting nodes.pkl: {e}")
        import traceback
        traceback.print_exc()

def main():
    # Define the data directory
    data_dir = Path("data/trainticket")
    
    if not data_dir.exists():
        print(f"Directory {data_dir} does not exist!")
        return
    
    # Convert each pkl file
    pkl_files = {
        'traces.pkl': convert_traces_pkl,
        'spanLabels.pkl': convert_span_labels_pkl,
        'nodes.pkl': convert_nodes_pkl
    }
    
    for pkl_file, converter_func in pkl_files.items():
        pkl_path = data_dir / pkl_file
        csv_path = data_dir / pkl_file.replace('.pkl', '.csv')
        
        if pkl_path.exists():
            converter_func(str(pkl_path), str(csv_path))
            print("-" * 50)
        else:
            print(f"File {pkl_path} does not exist!")

if __name__ == "__main__":
    main()
