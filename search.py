import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import requests
from PIL import Image
from io import BytesIO
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from tempfile import NamedTemporaryFile
import os

# Define the scopes
scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Load credentials from Streamlit secrets
google_creds = st.secrets["google_sheets"]
# Ensure the credentials are used with the defined scopes
creds = Credentials.from_service_account_info(google_creds, scopes=scopes)

# Authorize the client with the credentials
client = gspread.authorize(creds)

# Open the spreadsheet
sheet = client.open("Kendra Javabdars information").sheet1
data = sheet.get_all_records()

# Convert to DataFrame
df = pd.DataFrame(data)
# Define a function to apply styling to the information displayed
def styled_write(label, value):
    if value and value != 'N/A':
        # Use markdown with custom styles for better formatting
        st.markdown(f"<div style='font-weight: bold;'>{label}:</div> {value}", unsafe_allow_html=True)
    else:
        # Lighter text for N/A values
        st.markdown(f"<div style='font-weight: bold; color: #888;'>{label}:</div> N/A", unsafe_allow_html=True)

# Define some CSS to style the cards and the main container
st.markdown("""
<style>
.card {
    padding: 10px;
    border-radius: 10px;
    margin: 10px 0;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    display: inline-block;
    width: 100%;
}
.main-container {
    padding: 20px;
}
</style>
""", unsafe_allow_html=True)
# Function to get image from Google Drive
def get_image_from_drive(file_id, credentials):
    service = build('drive', 'v3', credentials=credentials)

    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False

    while not done:
        status, done = downloader.next_chunk()

    fh.seek(0)
    return fh
# Function to get image from Google Drive, display it, and delete it
# def display_and_delete_image(file_id, credentials):
#     image_stream = get_image_from_drive(file_id, credentials)
#     if image_stream:
#         # Create a temporary file to hold the image
#         with NamedTemporaryFile(delete=False, suffix='.png') as tmp:
#             tmp.write(image_stream.read())
#             tmp.flush()  # Write out all data to disk
#             st.image(tmp.name, width=200)  # Display the image in Streamlit
#         # Delete the temporary file - this can be omitted if delete=True in NamedTemporaryFile
#         os.unlink(tmp.name)
def display_image(image_url):
    if 'drive.google.com' in image_url:
        # Extract the file ID and format URL for direct access
        file_id = image_url.split('id=')[1]
        image_stream = get_image_from_drive(file_id, creds)
        image = Image.open(image_stream)
        st.image(image, use_column_width=True)
    else:
        # For direct image URLs, you can use the URL directly
        st.image(image_url, use_column_width=True)

# Streamlit app interface
st.title('Search')

# File uploader for categories.csv
uploaded_file = st.file_uploader("Upload your categories.csv", type="csv")

if uploaded_file:
    categories_df = pd.read_csv(uploaded_file)
    category_to_columns = {category: [col for col in columns if pd.notnull(col)]
                           for category, columns in categories_df.items()}  # Changed iteritems() to items()


# Search form
search_query = st.text_input("Search by any field", "")

if st.button("Search") and search_query:
    search_query = search_query.lower()  # Case-insensitive search
    filtered_df = df[df.apply(lambda row: row.astype(str).str.lower().str.contains(search_query).any(), axis=1)]
    
    # Assuming 'category_to_columns' is already defined based on the uploaded CSV

    if not filtered_df.empty:
        for _, row in filtered_df.iterrows():
            # Create a layout with an image on the left and details on the right
            cols = st.columns((1, 1))  # Adjust the ratio to your liking
            
            with cols[0]:  # Left column for the image
                if pd.notnull(row.get('Image URL', '')):
                    try:
                        # Assuming you have a function to handle image display
                        display_image(row['Image URL'])  # Function to display image
                    except Exception as e:
                        st.error(f"An error occurred while displaying the image: {e}")

            with cols[1]:  # Right column for the details
                # Now iterate over categories and their corresponding columns
                for category, columns in category_to_columns.items():
                    st.subheader(category)
                    for col in columns:
                        # Check if value exists and is not null
                        value = row.get(col, "N/A")
                        # Display the value with bold label using markdown
                        st.markdown(f"**{col}:** {value}")
                
            st.markdown("---")  # Separator for different entries

    else:
        st.error("No matching records found.")
