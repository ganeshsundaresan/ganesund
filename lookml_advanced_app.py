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
            # If JSON is a list of dictionaries, treat as a flat file
            if isinstance(raw_json, list):
                return pd.json_normalize(raw_json)
            elif isinstance(raw_json, dict):
                # Flatten the dictionary if needed
                return pd.json_normalize(raw_json)
            else:
                st.error("⚠️ Unsupported JSON format.")
                return None
        elif uploaded_file.name.endswith(('.yaml', '.yml')):
            raw_yaml = yaml.safe_load(uploaded_file)
            # Handle YAML similarly to JSON
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

# ----------------------- Convert LookML to YAML -----------------------
def convert_to_yaml(lookml_content):
    return yaml.dump(lookml_content, sort_keys=False)

# ----------------------- Streamlit App -----------------------
def main():
    st.set_page_config(page_title="LookML Generator", layout="wide")
    st.title("📊 Advanced LookML Generator")
    st.write("Upload CSV, JSON, or YAML and customize LookML views with field types and data type overrides.")

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

            if st.button("🚀 Generate LookML"):
                if not column_config:
                    st.error("❌ Please select at least one column as dimension or measure.")
                else:
                    lookml_content = generate_lookml_from_df(data, view_name, column_config)
                    st.success("✅ LookML Generated Successfully!")
                    st.code(lookml_content, language='yaml')

                    # Download Button
                    st.download_button(
                        label="📥 Download LookML",
                        data=lookml_content,
                        file_name=f"{view_name}.view.lkml",
                        mime="text/yaml"
                    )

if __name__ == "__main__":
    main()
