import yaml
import numpy as np
import pandas as pd
from pathlib import Path

# Configuration
input_csv = "data/henderson_segments.csv"
output_yaml = "data/henderson_network_altrios.yaml"
dummy_length = 3000.0
degree_to_rad = 0.0174533

def convert_numpy(obj):
    if isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]
    elif isinstance(obj, np.generic):
        return obj.item()
    else:
        return obj

def build_network():
    print(f"Reading {input_csv}...")
    df = pd.read_csv(input_csv)
    df = df.sort_values('beg_mp').reset_index(drop=True)
    
    df['cumulative_m'] = df['length_m'].cumsum()
    total_length_m = df['cumulative_m'].iloc[-1]
    
    print(f"Total Corridor Length: {total_length_m} meters")
    
    network_list = []
    
    def add_link(link_dict):
        link_dict['idx_next_alt'] = 0
        link_dict['idx_prev_alt'] = 0
        # Ensure length_meters field name is used if required (User sample used 'length', updated used 'length_meters')
        # Updated YAML head showed: 'length_meters: 0.0'.
        # Sample showed: 'length: 2000.0'.
        # I will use 'length_meters' to be safe for updated format.
        if 'length' in link_dict:
            link_dict['length_meters'] = link_dict.pop('length')
        network_list.append(link_dict)
    
    # Link 0
    add_link({
        'idx_curr': 0, 'idx_next': 0, 'idx_prev': 0, 'idx_flip': 0, 'length': 0.0,
        'elevs': [], 'headings': []
    })
    
    # Link 1: Dummy Start
    add_link({
        'idx_curr': 1, 'idx_next': 2, 'idx_prev': 0, 'idx_flip': 6,
        'length': dummy_length,
        'elevs': [{'offset': 0.0, 'elev': 0.0}, {'offset': dummy_length, 'elev': 0.0}],
        'headings': [{'offset': 0.0, 'heading': 0.0}, {'offset': dummy_length, 'heading': 0.0}],
        'speed_set': {'is_head_end': False, 'speed_limits': [{
            'offset_start_meters': 0.0, 
            'offset_end_meters': dummy_length, 
            'speed_meters_per_second': df.loc[0, 'speed'] * 0.44704
        }]}
    })

    # Link 2: Henderson
    elevs = []
    headings = []
    current_elev = 0.0
    current_heading = 0.0
    elevs.append({'offset': 0.0, 'elev': current_elev})
    headings.append({'offset': 0.0, 'heading': current_heading})
    running_offset = 0.0
    
    for i, row in df.iterrows():
        segment_len_m = row['length_m']
        grade_pct = row['grade_to_next']
        curve_deg = row['curvature_deg']
        running_offset += segment_len_m
        current_elev += (grade_pct / 100.0) * segment_len_m
        heading_change = curve_deg * row['length_ft'] * degree_to_rad * 10 
        current_heading += np.round(heading_change) / 1000.0
        norm_heading = ((current_heading * 1000) % 6283) / 1000.0
        elevs.append({'offset': float(np.round(running_offset, 3)), 'elev': float(current_elev)})
        headings.append({'offset': float(np.round(running_offset, 3)), 'heading': float(norm_heading)})

    # Precision Fix: Force last offset to match total_length exactly
    # Use total_length from dataframe cumsum, which running_offset tracks (with float noise?)
    # df['cumulative_m'].iloc[-1] IS total_length_m.
    # elevs[-1]['offset'] came from np.round output.
    # We set link length to total_length_m (float).
    # We update last points.
    
    elevs[-1]['offset'] = float(total_length_m)
    headings[-1]['offset'] = float(total_length_m)
    
    add_link({
        'idx_curr': 2, 'idx_next': 3, 'idx_prev': 1, 'idx_flip': 5,
        'length': float(total_length_m),
        'elevs': elevs,
        'headings': headings,
        'speed_set': {'is_head_end': False, 'speed_limits': [{
            'offset_start_meters': 0.0, 
            'offset_end_meters': float(total_length_m), 
            'speed_meters_per_second': df['speed'].mean() * 0.44704
        }]} 
    })

    # Link 3: Dummy End
    end_elev = elevs[-1]['elev']
    end_heading = headings[-1]['heading']
    add_link({
        'idx_curr': 3, 'idx_next': 0, 'idx_prev': 2, 'idx_flip': 4,
        'length': dummy_length,
        'elevs': [{'offset': 0.0, 'elev': end_elev}, {'offset': dummy_length, 'elev': end_elev}],
        'headings': [{'offset': 0.0, 'heading': end_heading}, {'offset': dummy_length, 'heading': end_heading}],
        'speed_set': {'is_head_end': False, 'speed_limits': [{
            'offset_start_meters': 0.0, 
            'offset_end_meters': dummy_length, 
            'speed_meters_per_second': df.iloc[-1]['speed'] * 0.44704
        }]}
    })

    # Link 4: Rev Start
    add_link({
        'idx_curr': 4, 'idx_next': 5, 'idx_prev': 0, 'idx_flip': 3,
        'length': dummy_length,
        'elevs': [{'offset': 0.0, 'elev': end_elev}, {'offset': dummy_length, 'elev': end_elev}], 
        'headings': [{'offset': 0.0, 'heading': (end_heading + 3.14159) % 6.283}, {'offset': dummy_length, 'heading': (end_heading + 3.14159) % 6.283}],
        'speed_set': network_list[3]['speed_set']
    })

    # Link 5: Rev Henderson
    rev_elevs = []
    rev_headings = []
    df_rev = df.iloc[::-1].reset_index(drop=True)
    rev_running_offset = 0.0
    rev_current_elev = end_elev
    rev_current_heading = (end_heading + 3.14159) % 6.283
    rev_elevs.append({'offset': 0.0, 'elev': rev_current_elev})
    rev_headings.append({'offset': 0.0, 'heading': rev_current_heading})
    
    for i, row in df_rev.iterrows():
        segment_len_m = row['length_m']
        grade_pct = row['grade_to_next'] * -1.0
        curve_deg = row['curvature_deg'] * -1.0
        rev_running_offset += segment_len_m
        rev_current_elev += (grade_pct / 100.0) * segment_len_m
        heading_change = curve_deg * row['length_ft'] * degree_to_rad * 10
        rev_current_heading += np.round(heading_change) / 1000.0
        norm_rev_heading = ((rev_current_heading * 1000) % 6283) / 1000.0
        rev_elevs.append({'offset': float(np.round(rev_running_offset, 3)), 'elev': float(rev_current_elev)})
        rev_headings.append({'offset': float(np.round(rev_running_offset, 3)), 'heading': float(norm_rev_heading)})
    
    # Precision Fix Rev
    rev_elevs[-1]['offset'] = float(total_length_m)
    rev_headings[-1]['offset'] = float(total_length_m)
        
    add_link({
        'idx_curr': 5, 'idx_next': 6, 'idx_prev': 4, 'idx_flip': 2,
        'length': float(total_length_m),
        'elevs': rev_elevs,
        'headings': rev_headings,
        'speed_set': network_list[2]['speed_set']
    })
    
    # Link 6: Rev End
    add_link({
        'idx_curr': 6, 'idx_next': 0, 'idx_prev': 5, 'idx_flip': 1,
        'length': dummy_length,
        'elevs': [{'offset': 0.0, 'elev': rev_current_elev}, {'offset': dummy_length, 'elev': rev_current_elev}],
        'headings': [{'offset': 0.0, 'heading': norm_rev_heading}, {'offset': dummy_length, 'heading': norm_rev_heading}],
        'speed_set': network_list[1]['speed_set']
    })

    # Wrap in Tolerances List
    tolerances = {
        "max_grade": 0.2, # generous
        "max_curv_radians_per_meter": 0.1,
        "max_heading_step_radians": 1.0,
        "max_elev_step_meters": 1000.0
    }
    
    final_data = [tolerances, network_list]

    clean_data = convert_numpy(final_data)
    with open(output_yaml, "w") as f:
        yaml.dump(clean_data, f, default_flow_style=False)
    
    print(f"Network Saved to {output_yaml} (Updated Format)")

if __name__ == "__main__":
    build_network()
