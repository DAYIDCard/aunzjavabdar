import streamlit as st
import pandas as pd
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread
import datetime
import os
import re
# import cv2
import numpy as np
from PIL import Image
from PIL import ImageOps
# from streamlit_back_camera_input import back_camera_input
from streamlit_cropper import st_cropper
import time

st.set_page_config(page_title="Javabdar Information", page_icon="form.png", layout="centered")

# Set up Google Sheets and Drive access
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_INFO = json.loads(st.secrets["gcp_service_account"])
credentials = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)

client = gspread.authorize(credentials)
drive_service = build('drive', 'v3', credentials=credentials)

SHEET_ID = st.secrets["SHEET_ID"]
FOLDER_ID = st.secrets["FOLDER_ID"]
DEV_SHEET_ID = st.secrets["DEV_SHEET_ID"]
DEV_FOLDER_ID = st.secrets["DEV_FOLDER_ID"]
credentials = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)

client = gspread.authorize(credentials)
drive_service = build('drive', 'v3', credentials=credentials)


# Simple login
password = st.text_input("Enter the access code", type="password", autocomplete="off")

if password == st.secrets["password"]:
    # Access code matches the password in secrets
    #pass
    st.write("Jay Yogeshwar. We have now closed the site for new entries.  If you are trying to update your photo, please go to https://dayphoto.streamlit.app/ and follow the instructions that were emailed to you. Please email dayidcard@gmail.com for any questions or concerns.")
    st.stop()
elif password == st.secrets["password2"]:
    pass
elif password == st.secrets["dev_password"]:
    # Access code matches the dev_password in secrets
    SHEET_ID = st.secrets["DEV_SHEET_ID"]
    FOLDER_ID = st.secrets["DEV_FOLDER_ID"]
else:
    # Access code does not match any password
    st.stop()

def disable():
    st.session_state.disabled = True
def enable():
    if "disabled" in st.session_state and st.session_state.disabled == True:
        st.session_state.disabled = False
if "disabled" not in st.session_state:
    st.session_state.disabled = False

def display_pil_image(pil_img):
    # Convert PIL Image to Bytes
    bytes_io = BytesIO()
    pil_img.save(bytes_io, format='PNG')

def detect_and_crop_face(image_file):
    # Load the pre-trained model for face detection
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

    # Convert the file to an OpenCV image
    file_bytes = np.asarray(bytearray(image_file.read()), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, 1)

    # Convert the image to grayscale (necessary for face detection)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Detect faces in the image
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    # If a face is detected, crop the face region
    if len(faces) > 0:
        for (x, y, w, h) in faces:
            # Adjust the frame to make sure we get a somewhat larger region that includes the whole head
            delta = max(w, h) // 2
            center_x, center_y = x + w // 2, y + h // 2
            x1, y1, x2, y2 = center_x - delta, center_y - delta, center_x + delta, center_y + delta
            
            # Crop and return the first face found (for simplicity)
            cropped_img = img[max(0, y1):y2, max(0, x1):x2]
            return cv2.cvtColor(cropped_img, cv2.COLOR_BGR2RGB)  # Convert color back to RGB
    
    # If no faces are detected, return None
    return None
# Function to get unique sorted values for a column, excluding NaN
def get_unique_sorted_values(array):
    return sorted(list(pd.Series(array).dropna().unique()))

def load_hierarchical_data(file_path):
    df = pd.read_csv(file_path)
    hierarchy = {}
    for _, row in df.iterrows():
        zone, cluster, kendra = row['Zone'], row['Cluster'], row['Kendra']
        if pd.notna(zone) and pd.notna(cluster):
            if zone not in hierarchy:
                hierarchy[zone] = {}
            if cluster not in hierarchy[zone]:
                hierarchy[zone][cluster] = []
            if pd.notna(kendra):
                hierarchy[zone][cluster].append(kendra)
    return hierarchy

# Now call the function with the file path
zone_cluster_kendra_mapping = load_hierarchical_data("dropdowns.csv")


# Function to load dropdown options and handle year formatting
def load_and_format_dropdowns(file_path):
    # Specify dtype as str to ensure all data is read as strings
    dropdowns_df = pd.read_csv(file_path, dtype=str)
    dropdown_options = {}
    multiselect_options = {}

    for col in dropdowns_df.columns:
        is_multiselect = col.endswith('_M')
        # Drop NaN values and ensure unique options
        options = dropdowns_df[col].dropna().unique().tolist()
        
        # Clean empty strings and whitespace
        options = [option.strip() for option in options if option and option.strip()]

        # Assign formatted options to the correct dictionary
        if is_multiselect:
            multiselect_options[col.rstrip('_M')] = options
        else:
            dropdown_options[col] = options

    return dropdown_options, multiselect_options

# Function to update clusters based on selected zone
def update_clusters():
    selected_zone = st.session_state['selected_zone']
    if selected_zone != 'Select a Zone':
        clusters = list(zone_cluster_kendra_mapping[selected_zone].keys())
        st.session_state['clusters'] = ['Select a Cluster'] + clusters
    else:
        st.session_state['clusters'] = ['Select a Cluster']
    st.session_state['selected_cluster'] = 'Select a Cluster'
# Function to resize the image
def resize_image(input_image, base_width=300):
    w_percent = (base_width / float(input_image.size[0]))
    h_size = int((float(input_image.size[1]) * float(w_percent)))
    resized_image = input_image.resize((base_width, h_size), Image.Resampling.LANCZOS)  # Use Resampling.LANCZOS for better quality
    return resized_image
# Function to update kendras based on selected cluster
def update_kendras():
    selected_zone = st.session_state['selected_zone']
    selected_cluster = st.session_state['selected_cluster']
    if selected_zone != 'Select a Zone' and selected_cluster != 'Select a Cluster':
        kendras = zone_cluster_kendra_mapping[selected_zone][selected_cluster]
        st.session_state['kendras'] = ['Select a Kendra'] + kendras
    else:
        st.session_state['kendras'] = ['Select a Kendra']
    st.session_state['selected_kendra'] = 'Select a Kendra'

# Initialize session state
if 'selected_zone' not in st.session_state:
    st.session_state['selected_zone'] = 'Select a Zone'
if 'clusters' not in st.session_state:
    st.session_state['clusters'] = ['Select a Cluster']
if 'selected_cluster' not in st.session_state:
    st.session_state['selected_cluster'] = 'Select a Cluster'
if 'kendras' not in st.session_state:
    st.session_state['kendras'] = ['Select a Kendra']
if 'selected_kendra' not in st.session_state:
    st.session_state['selected_kendra'] = 'Select a Kendra'
# Initialize session states
if 'confirmed_submission' not in st.session_state:
    st.session_state['confirmed_submission'] = False
if 'input_data' not in st.session_state:
    st.session_state['input_data'] = {}
# Load and preprocess CSV data
def preprocess_csv(file_path):
    df = pd.read_csv(file_path, header=None)
    processed_data = []
    for category in df.columns:
        fields = df[category].dropna().tolist()
        category_name = fields.pop(0)  # The first item is the category name
        for field in fields:
            processed_data.append({'Category': category_name, 'Field': field})
    return pd.DataFrame(processed_data)

categories_df = preprocess_csv("categories.csv")
def preprocess_fields(df):
    mandatory_fields = []
    all_fields = []
    for col in df.columns:
        for item in df[col].dropna():
            all_fields.append(item)
            if "*" in item:
                mandatory_fields.append(item.strip("*").strip())
    return mandatory_fields, all_fields

mandatory_fields, all_fields = preprocess_fields(categories_df)
def clear_form():
    # Reset session state variables
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    # Rerun the app to clear the form and refresh the state
    st.rerun()

# Load dropdowns.csv and prepare options
dropdowns_df = pd.read_csv("dropdowns.csv")

dropdown_options = {col: dropdowns_df[col].dropna().unique().tolist() for col in dropdowns_df.columns if not col.endswith('_M')}
multiselect_options = {col.rstrip('_M'): dropdowns_df[col].dropna().unique().tolist() for col in dropdowns_df.columns if col.endswith('_M')}

# Function to crop the image automatically
# def crop_image(image):
#     try:
#         # Detect and crop the face in the image
#         cropped_image = detect_and_crop_face(image)
#         return cropped_image
#     except Exception as e:
#         st.error(f"An error occurred: {e}")
#         return None

# UI Building
st.title('Javabdar Information Form')
st.markdown("Select your :red[***home***] Zone, Cluster and Kendra.")
col1, col2, col3 = st.columns(3)
with col1:
    selected_zone = st.selectbox('Zone *', ['Select a Zone'] + sorted(zone_cluster_kendra_mapping.keys()), index=0, key='selected_zone', on_change=update_clusters)
with col2:
    selected_cluster = st.selectbox('Cluster *', st.session_state['clusters'], index=0, key='selected_cluster', on_change=update_kendras)
with col3:
    selected_kendra = st.selectbox('Kendra *', st.session_state['kendras'], index=0, key='selected_kendra')


# Image upload options
st.markdown("Provide a picture of yourself :red[with your ***spouse***].")
st.write(" :exclamation: Please use an appropriate higher resolution image as this will be printed :exclamation:")
#upload_option = st.radio("Choose an option", ("Upload Image", "Take a Photo"))

image = None

#if upload_option == "Upload Image":
uploaded_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], accept_multiple_files=False, key='uploaded_file')

if uploaded_file is not None:
    ext = os.path.splitext(uploaded_file.name)[-1].lower()
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)
    if ext == ".png":
        #st.write("This is a png file")
        image = image.convert("RGB")
        #st.write("after convert")
        #image=os.path.splitext(uploaded_file.name)[0] + ".jpg"
        #st.write(image)
#elif upload_option == "Take a Photo":
#   camera_image = st.camera_input("Take a photo",)

#    if camera_image is not None:
#        image = Image.open(camera_image)

    # base_width = 300  # You can dynamically adjust this if you manage to get screen width via JavaScript in Streamlit
    # image = resize_image(image, base_width)

# Image cropping functionality
if image is not None:
    # if upload_option == "Upload Image":
    #     st.image(image, caption='Uploaded Image', use_column_width=True)
    st.write("Adjust the square box to select the portion of the image to save")
    #st.write(":exclamation: Double click on the image to save the cropped image :exclamation:")
    # Cropping tool
    cropped_img = st_cropper(image, aspect_ratio=(1, 1), realtime_update=True, key='cropper')

    # if st.button("Confirm Crop"):
    if cropped_img is not None:

        st.image(cropped_img, caption='Image that will be submitted', use_column_width=True)

        image = cropped_img

        st.write("Please fill out the form below:")
            
        last_category = None  # Initialize last_category before the loop
        mandatory_fields_filled = True
        is_email_valid = True
        is_phone_valid = True

        with st.form("Krutisheel_Information_Form", clear_on_submit=False):
            input_data = {}
            last_category = None  # Track the last category to group inputs by category
            mandatory_fields_filled = True  # Assume all mandatory fields are filled initially

            for _, row in categories_df.iterrows():
                category, field = row['Category'], row['Field']
                is_mandatory = "*" in field
                # clean_field_name = field.replace("*", "").strip()
                field_key = f"{category}_{field}".replace(" ", "_").lower()
                input_data['selected_zone'] = selected_zone
                input_data['selected_cluster'] = selected_cluster
                input_data['selected_kendra'] = selected_kendra
                # Group inputs by category with a header
                if category != last_category:
                    if last_category is not None:  # Skip adding a separator before the first category
                        st.markdown("---")
                    st.subheader(category)
                    last_category = category

                # Creating form fields based on field type
                if "Year" in field:
                    years = list(range(datetime.datetime.now().year, 1949, -1))
                    input_data[field_key] = st.selectbox(field, [''] + list(map(str, years)), key=field_key)
                elif "Email" in field:
                    input_data[field_key] = st.text_input(field, key=field_key)
                    is_email_valid = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b', input_data[field_key])
                elif "Phone" in field:
                    input_data[field_key] = st.text_input(field, key=field_key)
                    if input_data[field_key]:
                        input_data[field_key] = ''.join(filter(str.isdigit, input_data[field_key]))
                        # Valid phone number only if its len is either 11 or 10 after removing non digits
                        if len(input_data[field_key]) in (11, 10):
                            input_data[field_key] = input_data[field_key][-10:]
                        else:
                            is_phone_valid = False
                        
                elif "Gender" in field:
                    input_data[field_key] = st.radio(field, ["Male", "Female"], key=field_key)
                elif field in dropdown_options:  # Assuming dropdown_options is prepared
                    input_data[field_key] = st.selectbox(field, [''] + dropdown_options[field], key=field_key)
                elif field in multiselect_options:  # Assuming multiselect_options is prepared
                    input_data[field_key] = st.multiselect(field, multiselect_options[field], key=field_key)
                elif "International Bhaktiferi" in field:
                    intl_message = '<p style="font-family:Source Sans Pro; color:Red; font-size: 12px;">Intl Bhaktiferi only applicable from North America but excluding to India.</p>'
                    st.markdown(intl_message, unsafe_allow_html=True)
                    col1, col2 = st.columns(2)
                    with col1:
                        intl_from = st.selectbox('International Bhaktiferi From', options=[''] + [str(year) for year in range(2024, 1980, -1)], index=0, key=f"input_{field.lower().replace(' ', '_')}_from", help="from N.A. excluding to India")
                    with col2:
                        intl_to = st.selectbox('International Bhaktiferi To', options=[''] + [str(year) for year in range(2024, 1980, -1)], index=0, key=f"input_{field.lower().replace(' ', '_')}_to", help="from N.A. excluding to India")
                    if intl_from:
                       input_data[field_key] = f"{intl_from} to {intl_to}"
                    else:
                        input_data[field_key] = ""
                else:
                    input_data[field_key] = st.text_input(field, key=field_key)

                # Check if this mandatory field is filled (for enabling the submit button)
                if is_mandatory and not input_data[field_key]:
                    mandatory_fields_filled = False

                
            submit_button = st.form_submit_button("Confirm submission", disabled=st.session_state.disabled)

        if submit_button:
            
            with st.spinner('Uploading image and appending data...'):
                # Process the image if uploaded
                # st.write("Submitted data:")
                # data = {'Field': [], 'Value': []}
                # for key, value in input_data.items():
                #     data['Field'].append(key)
                #     data['Value'].append(value)
                # df = pd.DataFrame(data)
                # st.table(df)
                # st.write(mandatory_fields)
                # st.write(categories_df)
                image_id = None
                # scan through the input_data and check if fields with * in their name are filled
                if all(value for key, value in input_data.items() if '*' in key) and selected_zone != "Select a Zone" and selected_cluster != "Select a Cluster" and selected_kendra != "Select a Kendra" and is_email_valid and is_phone_valid:
                    # all mandatory fields are filled
                    disable()
                    st.success("All mandatory fields are filled.")   
                    if image is not None:
                        # Assuming 'zone', 'cluster', 'first_name', 'middle_name', 'last_name' are keys in input_data
                        filename = f"{input_data['selected_zone']}_{input_data['selected_cluster']}_{input_data['information_about_yourself_first_name_*']}_{input_data['information_about_yourself_middle_name_*']}_{input_data['information_about_yourself_last_name_*']}_{input_data['information_about_yourself_birth_year_*']}.jpg"
                        filepath = f"./{filename}"
                        image.save(filepath, "JPEG")
                        
                        # Upload the image to Google Drive
                        file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
                        media = MediaFileUpload(filepath, mimetype='image/jpeg')
                        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
                        image_id = file.get('id')
                        
                        st.success("Image uploaded successfully.")
                        image_link = f"https://drive.google.com/uc?id={image_id}"
                    else:
                        image_link = "No image uploaded"
                    
                    # Append data to Google Sheet
                    try:
                        input_data['filename'] = filename
                        worksheet = client.open_by_key(SHEET_ID).sheet1
                        row_data = [str(value) for value in input_data.values()] + [image_link, datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                        worksheet.append_row(row_data)
                        st.success("Thank you. Your data has been successfully submitted! You may close the tab/browser now or reload the page if you need to submit another form.")
                        st.toast('Thank you. Your data has been successfully submitted!', icon='👍')
                        time.sleep(1)
                        st.toast('You may close the tab/browser now.', icon='👍')
                        # Reset the form

                        # remove uploaded image from UI session state
                        if 'uploaded_file' in st.session_state:
                            del st.session_state['uploaded_file']

                        if 'cropped_img' in st.session_state:
                            del st.session_state['cropped_img']
                        # delete the uploaded image
                        if image is not None:
                            os.remove(filepath)
                        
                        #st.rerun()
                        # Clear the form
                        # st.form_submit_button("Reset form")
                        


                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                else:
                    if not is_email_valid:
                        st.error("Please enter a valid email address")
                        st.stop()
                    if not is_phone_valid:
                        st.error("Please enter a valid phone number")
                        st.stop()
                    # some mandatory fields are not filled
                    st.error("Please fill all mandatory fields marked with an asterisk (*) and select a Zone, Cluster, and Kendra before submitting.")
        if st.button("Reset Form"):
            clear_form()        
else:
    st.warning("Please Select Zone, Cluster, Kendra, and upload an image to continue. Additional details will need to be entered after the image is finalized.")
