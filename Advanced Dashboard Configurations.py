import streamlit as st
import pandas as pd
import yaml
import json

# ----------------------- Load Flat File -----------------------
def load_flat_file(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'):
            return pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith('.json'):
            raw_json = json.load(uploaded_file)
            if isinstance(raw_json, list):
                return pd.json_normalize(raw_json)
            elif isinstance(raw_json, dict):
                return pd.json_normalize(raw_json)
            else:
                st.error("⚠️ Unsupported JSON format.")
                return None
        elif uploaded_file.name.endswith(('.yaml', '.yml')):
            raw_yaml = yaml.safe_load(uploaded_file)
            if isinstance(raw_yaml, list):
                return pd.json_normalize(raw_yaml)
            elif isinstance(raw_yaml, dict):
                return pd.json_normalize(raw_yaml)
            else:
                st.error("⚠️ Unsupported YAML format.")
                return None
        else:
            st.error("❌ Unsupported file format. Please upload CSV, JSON, or YAML.")
            return None
    except Exception as e:
        st.error(f"⚠️ Error loading file: {e}")
        return None

# ----------------------- Generate LookML from DataFrame -----------------------
def generate_lookml_from_df(df, view_name, column_config):
    lookml_template = f"view: {view_name} {{\n  sql_table_name: ANALYTICS_DEV.GSUNDARESAN_CORE.{view_name} ;;\n\n"
    for col, config in column_config.items():
        col_lower = col.lower()
        field_type = config["field_type"]
        data_type = config["data_type"]

        if field_type == "dimension":
            lookml_template += f"  dimension: {col_lower} {{\n    type: {data_type}\n    sql: ${{TABLE}}.{col} ;;\n  }}\n\n"
        elif field_type == "measure":
            lookml_template += f"  measure: {col_lower} {{\n    type: {data_type}\n    sql: ${{TABLE}}.{col} ;;\n  }}\n\n"
    lookml_template += "}"
    return lookml_template

# ----------------------- Generate LookML Dashboard -----------------------
def generate_lookml_dashboard(dashboard_title, view_name, tile_configs):
    dashboard_template = {
        'dashboard': dashboard_title.lower().replace(" ", "_"),
        'title': dashboard_title,
        'layout': 'newspaper',
        'preferred_viewer': 'dashboards-next',
        'elements': []
    }

    for config in tile_configs:
        element = {
            'title': config['tile_title'],
            'name': config['tile_title'].lower().replace(" ", "_"),
            'model': config['model_name'],
            'explore': view_name,
            'type': config['tile_type'],
            'fields': config['selected_fields'],
            'pivots': config.get('pivots', []),
            'fill_fields': config.get('fill_fields', config['selected_fields']),
            'filters': config.get('filters', {}),
            'sorts': config.get('sorts', []),
            'limit': config.get('limit', 500),
            'column_limit': config.get('column_limit', 50),
            'query_timezone': config.get('timezone', 'America/Los_Angeles'),
            'row': config.get('row', 0),
            'col': config.get('col', 0),
            'width': config.get('width', 8),
            'height': config.get('height', 6),
            'show_view_names': config.get('show_view_names', False),
            'show_y_axis_labels': config.get('show_y_axis_labels', True),
            'show_x_axis_label': config.get('show_x_axis_label', True),
            'y_axis_scale_mode': config.get('y_axis_scale_mode', 'linear'),
            'x_axis_scale': config.get('x_axis_scale', 'auto'),
            'legend_position': config.get('legend_position', 'center'),
            'show_value_labels': config.get('show_value_labels', True),
            'dynamic_fields': config.get('dynamic_fields', [])
        }
        dashboard_template['elements'].append(element)

    return yaml.dump([dashboard_template], sort_keys=False, default_flow_style=False)

# ----------------------- Streamlit App -----------------------
def main():
    st.set_page_config(page_title="LookML Advanced Dashboard Generator", layout="wide")
    st.title("📊 LookML View & Advanced Dashboard Generator")
    st.write("Upload CSV, JSON, or YAML and generate LookML views and advanced dashboards interactively.")

    uploaded_file = st.file_uploader("📁 Upload CSV, JSON, or YAML File", type=["csv", "json", "yaml", "yml"])

    if uploaded_file:
        data = load_flat_file(uploaded_file)
        if data is not None:
            st.success("✅ Flat file loaded successfully!")
            st.write("### 🗂️ Data Preview")
            st.dataframe(data.head())

            # Input for View Name
            view_name = st.text_input("📋 Enter LookML View Name", value="MY_VIEW")

            # Initialize column config
            column_config = {}
            st.write("### 🔧 Configure Columns:")

            for col in data.columns:
                col_dtype = data[col].dtype
                default_field_type = "measure" if col_dtype in ['int64', 'float64'] else "dimension"
                default_data_type = "sum" if default_field_type == "measure" else "string"

                st.markdown(f"**Column:** `{col}`")
                field_type = st.selectbox(f"Select field type for `{col}`", ["dimension", "measure", "exclude"], index=0 if default_field_type == "dimension" else 1, key=f"field_{col}")
                data_type = st.text_input(f"Data type for `{col}`", value=default_data_type, key=f"data_{col}")

                if field_type != "exclude":
                    column_config[col] = {
                        "field_type": field_type,
                        "data_type": data_type
                    }

                st.write("---")

            if st.button("🚀 Generate LookML View"):
                if not column_config:
                    st.error("❌ Please select at least one column as dimension or measure.")
                else:
                    lookml_content = generate_lookml_from_df(data, view_name, column_config)
                    st.success("✅ LookML View Generated Successfully!")
                    st.code(lookml_content, language='yaml')

                    st.download_button(
                        label="📥 Download LookML View",
                        data=lookml_content,
                        file_name=f"{view_name}.view.lkml",
                        mime="text/yaml"
                    )

            # ------------------ Advanced Dashboard Creation ------------------
            st.write("### 🗂️ **Create Advanced LookML Dashboard**")
            dashboard_title = st.text_input("📊 Dashboard Title", value="My Advanced LookML Dashboard")
            num_tiles = st.number_input("🧱 Number of Tiles", min_value=1, max_value=10, value=2, step=1)

            tile_configs = []

            for i in range(num_tiles):
                st.subheader(f"Tile {i+1} Configuration")
                tile_title = st.text_input(f"Tile {i+1} Title", value=f"Tile {i+1}", key=f"tile_title_{i}")
                model_name = st.text_input(f"Model Name for Tile {i+1}", value="your_model_name", key=f"model_name_{i}")
                tile_type = st.selectbox(f"Tile Type for Tile {i+1}", ["looker_line", "looker_bar", "single_value", "looker_grid"], key=f"tile_type_{i}")
                selected_fields = st.multiselect(f"Select Fields for Tile {i+1}", data.columns.tolist(), key=f"fields_{i}")

                # Auto-suggest filters, pivots, and sorts based on dataset
                default_pivots = [col for col in data.columns if data[col].dtype == 'object' or 'date' in col.lower()]
                default_sorts = [col for col in data.columns if data[col].dtype in ['int64', 'float64']]
                sample_filters = {col: data[col].unique().tolist()[:3] for col in data.columns[:2]}  # First 2 columns with sample values

                pivots = st.text_area(f"Pivots for Tile {i+1} (comma-separated)", value=", ".join(default_pivots), key=f"pivots_{i}")
                fill_fields = st.text_area(f"Fill Fields for Tile {i+1} (comma-separated)", value=", ".join(selected_fields), key=f"fill_fields_{i}")
                filters = st.text_area(f"Filters (YAML format) for Tile {i+1}", value=yaml.dump(sample_filters), key=f"filters_{i}")
                sorts = st.text_area(f"Sort Fields (comma-separated)", value=", ".join(default_sorts), key=f"sorts_{i}")

                row = st.number_input(f"Row Position for Tile {i+1}", min_value=0, value=i * 8, key=f"row_{i}")
                col = st.number_input(f"Column Position for Tile {i+1}", min_value=0, value=0, key=f"col_{i}")
                width = st.number_input(f"Width for Tile {i+1}", min_value=1, value=8, key=f"width_{i}")
                height = st.number_input(f"Height for Tile {i+1}", min_value=1, value=6, key=f"height_{i}")

                tile_configs.append({
                    "tile_title": tile_title,
                    "model_name": model_name,
                    "tile_type": tile_type,
                    "selected_fields": [f"{view_name}.{field}" for field in selected_fields],
                    "pivots": [p.strip() for p in pivots.split(",")] if pivots else [],
                    "fill_fields": [f.strip() for f in fill_fields.split(",")] if fill_fields else [f"{view_name}.{field}" for field in selected_fields],
                    "filters": yaml.safe_load(filters) if filters else {},
                    "sorts": [s.strip() for s in sorts.split(",")] if sorts else [],
                    "row": row,
                    "col": col,
                    "width": width,
                    "height": height
                })

            if st.button("🛠️ Generate Advanced LookML Dashboard"):
                if not tile_configs:
                    st.error("❌ Please configure at least one tile.")
                else:
                    dashboard_yaml = generate_lookml_dashboard(dashboard_title, view_name, tile_configs)
                    st.success("✅ Advanced LookML Dashboard Generated Successfully!")
                    st.code(dashboard_yaml, language='yaml')

                    st.download_button(
                        label="📥 Download LookML Dashboard",
                        data=dashboard_yaml,
                        file_name=f"{dashboard_title.replace(' ', '_').lower()}.dashboard.lkml",
                        mime="text/yaml"
                    )

if __name__ == "__main__":
    main()
