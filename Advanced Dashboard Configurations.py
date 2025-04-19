import streamlit as st
import pandas as pd
import json
import yaml
from typing import Optional, Dict, Any, List

# ----------------------- Constants -----------------------
SUPPORTED_FILE_TYPES = ["csv", "json", "yaml", "yml"]
DEFAULT_MODEL_NAME = "your_model_name"
DEFAULT_VIEW_NAME = "your_view_name"
DEFAULT_DASHBOARD_TITLE = "My Advanced LookML Dashboard"
DEFAULT_TIMEZONE = "America/Los_Angeles"

# ----------------------- Helper Functions -----------------------
def to_lookml_name(name: str) -> str:
    """Converts a string to snake_case for LookML compatibility."""
    return name.lower().replace(" ", "_")

def infer_data_type(column: pd.Series) -> str:
    """Infers the data type of a Pandas Series."""
    if pd.api.types.is_datetime64_any_dtype(column):
        return "date"
    elif pd.api.types.is_numeric_dtype(column):
        return "number"
    else:
        return "string"

# ----------------------- File Loading -----------------------
def load_flat_file(uploaded_file) -> Optional[pd.DataFrame]:
    """Loads a flat file (CSV, JSON, YAML) into a Pandas DataFrame."""
    try:
        if uploaded_file.name.endswith(".csv"):
            return pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".json"):
            raw_json = json.load(uploaded_file)
            if isinstance(raw_json, list):
                return pd.json_normalize(raw_json)
            elif isinstance(raw_json, dict):
                return pd.json_normalize(raw_json)
            else:
                st.error("⚠️ Unsupported JSON format: Must be a list or dictionary.")
                return None
        elif uploaded_file.name.endswith((".yaml", ".yml")):
            raw_yaml = yaml.safe_load(uploaded_file)
            if isinstance(raw_yaml, list):
                return pd.json_normalize(raw_yaml)
            elif isinstance(raw_yaml, dict):
                return pd.json_normalize(raw_yaml)
            else:
                st.error("⚠️ Unsupported YAML format: Must be a list or dictionary.")
                return None
        else:
            st.error(f"❌ Unsupported file format. Please upload one of: {', '.join(SUPPORTED_FILE_TYPES)}")
            return None
    except Exception as e:
        st.error(f"⚠️ Error loading file: {e}")
        return None

# ----------------------- LookML Generation -----------------------
def generate_lookml_view(df: pd.DataFrame, view_name: str, column_config: Dict[str, Dict[str, str]], sql_table_name: str) -> str:
    """Generates a LookML view from a DataFrame and user-defined column configurations."""

    lookml_template = f"view: {view_name} {{\n"
    lookml_template += f"  sql_table_name: {sql_table_name} ;;\n\n"

    for col, config in column_config.items():
        col_lookml_name = to_lookml_name(col)
        field_type = config["field_type"]
        data_type = config["data_type"]

        if field_type == "dimension":
            if data_type in ["date", "datetime", "timestamp"]:
                lookml_template += f"  dimension_group: {col_lookml_name} {{\n"
                lookml_template += "    type: time\n"
                lookml_template += "    timeframes: [raw, date, week, month, quarter, year]\n"  # Added 'date'
                lookml_template += f"    sql: ${{TABLE}}.{col} ;;\n"
                lookml_template += "  }\n\n"
            else:
                lookml_template += f"  dimension: {col_lookml_name} {{\n"
                lookml_template += f"    type: {data_type}\n"
                lookml_template += f"    sql: ${{TABLE}}.{col} ;;\n"
                lookml_template += "  }\n\n"

        elif field_type == "measure":
            lookml_template += f"  measure: {col_lookml_name} {{\n"
            lookml_template += f"    type: {data_type}\n"
            lookml_template += f"    sql: ${{TABLE}}.{col} ;;\n"
            lookml_template += "  }\n\n"

    lookml_template += "}"
    return lookml_template

def generate_lookml_dashboard(dashboard_title: str, view_name: str, tile_configs: List[Dict[str, Any]]) -> str:
    """Generates a LookML dashboard from user-defined configurations."""

    dashboard_name = to_lookml_name(dashboard_title)

    dashboard_template = {
        'dashboard': dashboard_name,
        'title': dashboard_title,
        'layout': 'newspaper',
        'preferred_viewer': 'dashboards-next',
        'elements': []
    }

    for config in tile_configs:
        element = {
            'title': config['tile_title'],
            'name': to_lookml_name(config['tile_title']),
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
            'query_timezone': config.get('timezone', DEFAULT_TIMEZONE),  # Use the constant
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
    st.title("🔍 My Advanced LookML Dashboard")

    # File Upload Section
    uploaded_file = st.file_uploader(
        "Upload CSV, JSON, or YAML file", type=SUPPORTED_FILE_TYPES
    )

    if uploaded_file is not None:
        data = load_flat_file(uploaded_file)

        if data is not None:
            st.write("### 🗂️ Data Preview")
            st.dataframe(data.head())

            # View Configuration
            st.write("### ⚙️ View Configuration")
            view_name = st.text_input("View Name", value=DEFAULT_VIEW_NAME)
            sql_table_name = st.text_input("SQL Table Name", value=f"ANALYTICS_DEV.GSUNDARESAN_CORE.{view_name}")

            column_config = {}
            st.write("### 🔧 Configure Columns:")

            for col in data.columns:
                st.markdown(f"**Column:** `{col}`")
                col_dtype = data[col].dtype
                default_field_type = "dimension"
                default_data_type = infer_data_type(data[col])

                field_type = st.selectbox(
                    f"Field type for `{col}`",
                    ["dimension", "measure", "exclude"],
                    index=0 if default_field_type == "dimension" else 1,
                    key=f"field_{col}",
                )

                if field_type == "exclude":
                    continue

                data_type = st.selectbox(
                    f"Data type for `{col}`",
                    ["string", "number", "date", "yesno"],  # Added 'yesno'
                    index=["string", "number", "date", "yesno"].index(default_data_type),
                    key=f"data_{col}",
                )

                column_config[col] = {
                    "field_type": field_type,
                    "data_type": data_type,
                }
                st.write("---")

            if st.button("🚀 Generate LookML View"):
                if not column_config:
                    st.error("❌ Please configure at least one column as a dimension or measure.")
                else:
                    lookml_content = generate_lookml_view(data, view_name, column_config, sql_table_name)
                    st.success("✅ LookML View Generated Successfully!")
                    st.code(lookml_content, language="lookml")  # Use 'lookml' for syntax highlighting

                    st.download_button(
                        label="📥 Download LookML View",
                        data=lookml_content,
                        file_name=f"{view_name}.view.lkml",
                        mime="text/plain",  # Changed to 'text/plain'
                    )

            # Dashboard Section
            st.write("### 🗂️ **Create Advanced LookML Dashboard**")
            dashboard_title = st.text_input("📊 Dashboard Title", value=DEFAULT_DASHBOARD_TITLE)
            num_tiles = st.number_input("🧱 Number of Tiles", min_value=1, max_value=10, value=2, step=1)

            tile_configs = []

            for i in range(num_tiles):
                st.subheader(f"Tile {i+1} Configuration")
                tile_title = st.text_input(f"Tile {i+1} Title", value=f"Tile {i+1}", key=f"tile_title_{i}")
                model_name = st.text_input(f"Model Name for Tile {i+1}", value=DEFAULT_MODEL_NAME, key=f"model_name_{i}")
                tile_type = st.selectbox(f"Tile Type for Tile {i+1}", ["looker_line", "looker_bar", "single_value", "looker_grid"], key=f"tile_type_{i}")

                # Fetching time-based and non-time-based fields
                date_fields = [col for col in data.columns if 'date' in col.lower() or pd.api.types.is_datetime64_any_dtype(data[col])]
                all_dimensions = list(data.columns) + [f"{col}_year" for col in date_fields] + [f"{col}_month" for col in date_fields]

                selected_fields = st.multiselect(f"Select Fields for Tile {i+1}", all_dimensions, key=f"fields_{i}")

                # Pivots
                pivot_options =  [None] + list(data.columns) + [f"{p}_year" for p in date_fields] + [f"{p}_week" for p in date_fields]

                pivots = st.selectbox(
                    f"Pivots for Tile {i+1}",
                    pivot_options,
                    key=f"pivots_{i}"
                )
                # Ensure that when no pivot is selected, an empty list is passed to the dashboard config
                pivots_list = [pivots] if pivots else []

                # Fill Fields
                fill_fields = st.multiselect(f"Fill Fields for Tile {i+1}", selected_fields, key=f"fill_fields_{i}")

                # Filters
                filters = st.multiselect(
                    f"Filters for Tile {i+1} (Natural Language)",
                    [f"{f} in last 30 days" for f in date_fields] +
                    [f"{f} in last 7 days" for f in date_fields],
                    key=f"filters_{i}"
                )

                # Sorting
                sorts = st.selectbox(f"Sort Fields for Tile {i+1}", all_dimensions, key=f"sorts_{i}")

                # Layout
                row = st.number_input(f"Row Position for Tile {i+1}", min_value=0, value=i * 8, key=f"row_{i}")
                col = st.number_input(f"Column Position for Tile {i+1}", min_value=0, value=0, key=f"col_{i}")
                width = st.number_input(f"Width for Tile {i+1}", min_value=1, value=8, key=f"width_{i}")
                height = st.number_input(f"Height for Tile {i+1}", min_value=1, value=6, key=f"height_{i}")

                # Style
                legend_position = st.selectbox(
                    f"Legend Position for Tile {i+1}",
                    ["center", "top", "bottom", "left", "right"],
                    key=f"legend_position_{i}"
                )
                timezone = st.selectbox(
                    f"Timezone for Tile {i+1}",
                    ["America/Los_Angeles", "UTC", "Europe/London"],
                    key=f"timezone_{i}"
                )

                tile_configs.append({
                    "tile_title": tile_title,
                    "model_name": model_name,
                    "tile_type": tile_type,
                    "selected_fields": [f"{view_name}.{to_lookml_name(field)}" for field in selected_fields],
                    "pivots": [to_lookml_name(p) for p in pivots_list] if pivots_list else [],
                    "fill_fields": [f"{view_name}.{to_lookml_name(field)}" for field in fill_fields],
                    "filters": filters,
                    "sorts": [to_lookml_name(sorts)] if sorts else [],
                    "row": row,
                    "col": col,
                    "width": width,
                    "height": height,
                    "legend_position": legend_position,
                    "timezone": timezone
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
                        file_name=f"{to_lookml_name(dashboard_title)}.dashboard.lkml",
                        mime="text/plain"
                    )

if __name__ == "__main__":
    main()
