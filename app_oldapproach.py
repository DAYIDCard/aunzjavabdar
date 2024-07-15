import streamlit as st
from google.oauth2.service_account import Credentials
import gspread
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import json
import datetime

# Define the scopes
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

# Load credentials
creds_json = json.loads(st.secrets["gcp_service_account"])  # Parse the JSON string into a Python dictionary
creds = Credentials.from_service_account_info(creds_json, scopes=SCOPES)
client = gspread.authorize(creds)

# Google Drive service
drive_service = build('drive', 'v3', credentials=creds)

# Your spreadsheet ID and folder ID
SHEET_ID = '10tue4_51dfFW-AfXFRiyyR3dHJZGK9TayBBmImikT3A'
FOLDER_ID = '1_BqzRspCD0ANY1-dZCJQD5C59qyy12ys'
sheet_name = 'main'

# Simple login
password = st.text_input("Enter the access code", type="password")
if password != st.secrets["password"]:
    st.stop()
# Set min and max years
min_year = 1920
max_year = datetime.datetime.now().year

# Set default date as today's date for the picker
default_date = datetime.datetime.now()

# Define a placeholder for the post-submission message and button
post_submit_placeholder = st.empty()
if 'ready_to_clear' not in st.session_state:
    st.session_state.ready_to_clear = False
# Define a function to clear all fields
def clear_form():
    # Keys for inputs are defined here; ensure they match those used in your widgets
    keys_to_clear = ['input_name', 'input_kendra', 'input_cluster', 'input_zone', 
                     'input_home_address', 'input_email', 'input_phone_number', 
                     'input_job_business', 'input_birthdate', 'input_current_karyakshetra', 
                     'input_current_karya_responsibility', 'input_current_karya_responsibility_spouse', 
                     'input_spouse_name', 'input_spouse_job_business', 'input_swadhyayee_years', 
                     'file_uploader_image'] + [f'input_child_{i+1}_name' for i in range(4)]
    
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
if 'submitted' not in st.session_state:
    st.session_state['submitted'] = False
if 'reset_form' not in st.session_state:
    st.session_state.reset_form = False
# Check and clear form if requested
if st.session_state.reset_form:
    clear_form()
    st.session_state.reset_form = False  # Reset the flag

# Streamlit form for data collection
with st.form('data_form', clear_on_submit=True):
    st.title('Krutisheel Information')
    
    # Personal Information Split into First, Middle, and Last Names
    first_name = st.text_input('First Name', key='input_first_name')
    middle_name = st.text_input('Middle Name', key='input_middle_name')
    last_name = st.text_input('Last Name', key='input_last_name')
    
    # Home Address broken down into components
    home_address = st.text_input('Home Address', key='input_street_address')
    city = st.text_input('City', key='input_city')
    state_province = st.text_input('State/Province', key='input_state_province')
    zip_pin = st.text_input('ZIP/PIN', key='input_zip_pin')
    # add email and validate if its a valid email with @ and .
    email = st.text_input('Email', key='input_email')
    # Validate email if user has entered something
    if email and (not '@' in email or not '.' in email):
        st.write('Please enter a valid email address')
        st.stop()


    # Job/Business
    profession = st.text_input('Profession', key='input_job_business')
    # Modified Birthdate Input for Month and Year only
    birth_month_year = st.selectbox('Birth Month and Year', 
                                    options=[datetime.date(year, month, 1).strftime('%b-%Y') 
                                             for year in range(min_year, max_year+1) 
                                             for month in range(1, 13)], 
                                    index=756, 
                                    key='input_birth_month_year')

    # Continuing with other fields based on your arrangement...
    phone_number = st.text_input('Phone Number', key='input_phone_number')
    # Format phone number to North America format (XXX) XXX-XXXX
    if len(phone_number) == 10:
        formatted_phone_number = f"({phone_number[:3]}) {phone_number[3:6]}-{phone_number[6:]}"
    else:
        st.write("Please enter a valid phone number.")
    
    # Zone, Cluster, and Kendra
    zone = st.text_input('Zone', key='input_zone')
    cluster = st.text_input('Cluster', key='input_cluster')
    kendra = st.text_input('Kendra', key='input_kendra')

    # Additional fields as specified...
    swadhyayee_years = st.number_input('Involved in Swadhyay Since (number of years)', min_value=0, step=1, key='input_swadhyayee_years')
    current_karyakshetra = st.text_input('Current Karyakshetras involved in', key='input_current_karyakshetra')
    current_karya_responsibility = st.text_area('Current Karya Responsibility for yourself', key='input_current_karya_responsibility')
    spouse_name = st.text_input("Spouse's Name", key='input_spouse_name')
    spouse_profession = st.text_input("Spouse's Profession", key='input_spouse_profession')
    spouse_swadhyayee_years = st.number_input("Spouse Involved in Swadhyay since:", min_value=0, step=1, key='input_spouse_swadhyayee_years')
    spouse_current_karya_responsibility = st.text_area("Spouse's Current Karya Responsibility (if applicable)", key='input_spouse_current_karya_responsibility')
    children_names = [st.text_input(f"Child {i+1}'s Name", key=f'input_child_{i+1}_name') for i in range(4)]

    # Image upload
    image = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], key='file_uploader_image')
    image = st.camera_input('Take a photo', key='camera_input_image') if image is None else image
    
    # Form submission
    submitted = st.form_submit_button('Submit')

# Form submission handling, image processing, and data insertion into Google Sheet remains as previously implemented.

# Assuming 'data_to_insert' is the array to be inserted, adjust it to match the new data structure


if submitted and image:
    # Process and rename the image
    zone_value = zone.strip()  # Assuming 'zone' is collected from st.text_input('Zone')
    kendra_value = kendra.strip()  # Assuming 'kendra' is collected from st.text_input('Kendra')
    # first_name, *middle_names, last_name = name.split()  # Splits the name by spaces
    # middle_name = ' '.join(middle_names) if middle_names else ''
    filename = f"{zone_value}_{kendra_value}_{first_name}_{middle_name}_{last_name}.{image.name.split('.')[-1]}"
    filepath = f"/tmp/{filename}"
    with open(filepath, 'wb') as f:
        f.write(image.getbuffer())

    # Upload the image to Google Drive
    file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
    media = MediaFileUpload(filepath, mimetype='image/jpeg')
    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, webViewLink').execute()
    image_link = file.get('webViewLink')

    # Insert data into the spreadsheet
    try:
        sheet = client.open_by_key(SHEET_ID).worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        st.error(f"Worksheet named '{sheet_name}' not found.")
        st.stop()
    data_to_insert = [
        first_name, middle_name, last_name, home_address, city, state_province, zip_pin, email, formatted_phone_number, profession, birth_month_year, zone, cluster, kendra, swadhyayee_years, current_karyakshetra, current_karya_responsibility, spouse_name,
        spouse_profession, spouse_swadhyayee_years, spouse_current_karya_responsibility, *children_names, image_link
    ]
    sheet.append_row(data_to_insert)

    # Cleanup the temporary image
    os.remove(filepath)
    st.session_state['submitted'] = True
    st.success('Your information has been successfully submitted!')