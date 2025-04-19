import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import snowflake.connector
import boto3
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from botocore.exceptions import NoCredentialsError
from io import BytesIO

# Configuration
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')

SNOWFLAKE_CONFIG = {
    'user': os.getenv('SNOWFLAKE_USER'),
    'password': os.getenv('SNOWFLAKE_PASSWORD'),
    'account': os.getenv('SNOWFLAKE_ACCOUNT'),
    'warehouse': os.getenv('SNOWFLAKE_WAREHOUSE'),
    'database': os.getenv('SNOWFLAKE_DATABASE'),
    'schema': os.getenv('SNOWFLAKE_SCHEMA')
}

EMAIL_SENDER = os.getenv('EMAIL_SENDER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')

CATEGORY_KEYWORDS = {
    'travel': ['flight', 'airfare', 'uber', 'ola', 'taxi', 'train', 'bus', 'hotel'],
    'food': ['restaurant','swiggy','zomato','doordash', 'dinner', 'lunch', 'breakfast', 'cafe', 'meal', 'food'],
    'other': []
}

def send_email(subject, body, attachment, receiver_email):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_SENDER
    msg['To'] = receiver_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    part = MIMEBase('application', 'octet-stream')
    part.set_payload(attachment)
    encoders.encode_base64(part)
    part.add_header('Content-Disposition', f"attachment; filename=master_expense_report.xlsx")
    msg.attach(part)

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, receiver_email, msg.as_string())
        st.success(f"Email sent successfully to {receiver_email}")
    except Exception as e:
        st.error(f"Failed to send email: {e}")

def fetch_pdfs_from_s3():
    s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY, aws_secret_access_key=AWS_SECRET_KEY)
    pdf_files = []
    try:
        response = s3.list_objects_v2(Bucket=S3_BUCKET_NAME)
        for obj in response.get('Contents', []):
            if obj['Key'].endswith('.pdf'):
                pdf_obj = s3.get_object(Bucket=S3_BUCKET_NAME, Key=obj['Key'])
                pdf_files.append((obj['Key'], pdf_obj['Body'].read()))
    except NoCredentialsError:
        st.error("AWS credentials not found.")
    return pdf_files

# (Other helper functions remain unchanged)

# Streamlit App
st.title("📊 PDF Expense Reporting App")

source_choice = st.radio("Select PDF Source", ('Local Files', 'AWS S3 Bucket'))

pdf_files = []
if source_choice == 'Local Files':
    uploaded_files = st.file_uploader("Upload PDF files", type=['pdf'], accept_multiple_files=True)
    if uploaded_files:
        pdf_files = [(file.name, file.read()) for file in uploaded_files]
else:
    if st.button("Fetch PDFs from S3"):
        pdf_files = fetch_pdfs_from_s3()

if pdf_files:
    all_dataframes = []
    for file_name, pdf_bytes in pdf_files:
        text = extract_text_from_pdf(pdf_bytes)
        if not text:
            st.warning(f"Failed to extract text from {file_name}")
            continue

        passenger_name = extract_passenger_name(text)
        complexity = analyze_pdf_complexity(text)
        df = parse_text_to_dataframe(text, complexity)
        df = clean_dataframe(df)
        df['Passenger_Name'] = passenger_name
        all_dataframes.append(df)

    if all_dataframes:
        master_df = pd.concat(all_dataframes, ignore_index=True)
        st.dataframe(master_df)

        st.subheader("Overall Preview")
        st.write(master_df.describe(include='all'))

        excel_buffer = BytesIO()
        master_df.to_excel(excel_buffer, index=False)
        st.download_button("Download Master Expense Report", data=excel_buffer.getvalue(), file_name="master_expense_report.xlsx", mime="application/vnd.ms-excel")

        receiver_email = st.text_input("Enter receiver email for the report")
        if st.button("Send Report via Email"):
            send_email("Master Expense Report", "Please find the attached expense report.", excel_buffer.getvalue(), receiver_email)

        if st.button("Upload to Snowflake"):
            upload_to_snowflake(master_df, 'EXPENSE_REPORTS')
            st.success("Uploaded to Snowflake successfully!")
