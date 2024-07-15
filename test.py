import streamlit as st
import pandas as pd
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import gspread
import datetime

# Set up Google Sheets and Drive access
SCOPES = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_INFO = json.loads(st.secrets["gcp_service_account"])
credentials = Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO, scopes=SCOPES)

client = gspread.authorize(credentials)
drive_service = build('drive', 'v3', credentials=credentials)

SHEET_ID = '10tue4_51dfFW-AfXFRiyyR3dHJZGK9TayBBmImikT3A'
FOLDER_ID = '1_BqzRspCD0ANY1-dZCJQD5C59qyy12ys'

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

# Load dropdowns.csv and prepare options
dropdowns_df = pd.read_csv("dropdowns.csv")

dropdown_options = {col: dropdowns_df[col].dropna().unique().tolist() for col in dropdowns_df.columns if not col.endswith('_M')}
multiselect_options = {col.rstrip('_M'): dropdowns_df[col].dropna().unique().tolist() for col in dropdowns_df.columns if col.endswith('_M')}


# UI Building
st.title('Krutisheel Information Form')
selected_zone = st.selectbox('Zone', ['Select a Zone'] + sorted(zone_cluster_kendra_mapping.keys()), index=0, key='selected_zone', on_change=update_clusters)
selected_cluster = st.selectbox('Cluster', st.session_state['clusters'], index=0, key='selected_cluster', on_change=update_kendras)
selected_kendra = st.selectbox('Kendra', st.session_state['kendras'], index=0, key='selected_kendra')


with st.form("Krutisheel_Information_Form"):
    input_data = {}
    last_category = None

    for _, row in categories_df.iterrows():
        category = row['Category']
        field = row['Field']
        field_key = f"{category}_{field}".replace(" ", "_").lower()
        input_data['selected_zone'] = selected_zone
        input_data['selected_cluster'] = selected_cluster
        input_data['selected_kendra'] = selected_kendra

        # Check if we are in a new category to add the title and separator
        if category != last_category:
            st.markdown("---")  # Add a separator for visual distinction between categories
            st.subheader(category)  # Add the category title
            last_category = category
        
        # Special case for year selection fields
        if field == "Spouse Involved in Swadhyay since":
            # Here you can specify the range of years you want to show
            start_year = 1950
            end_year = datetime.datetime.now().year
            years = list(range(start_year, end_year + 1))
            input_data[field_key] = st.selectbox(field, years, key=field_key, index=years.index(2024))
        elif field == "Involved in Swadhyay since":
            start_year = 1950
            end_year = datetime.datetime.now().year
            years = list(range(start_year, end_year + 1))
            input_data[field_key] = st.selectbox(field, years, key=field_key, index=years.index(2024))
        elif field in dropdown_options:
            input_data[field_key] = st.selectbox(field, ['Select an option'] + dropdown_options[field], key=field_key)
        elif field in multiselect_options:
            input_data[field_key] = st.multiselect(field, multiselect_options[field], key=field_key)
        elif "Gender" in field:
            # Create radio buttons for Gender
            input_data[field] = st.radio(
                "Gender",
                options=["Male", "Female"],
                key=field_key
            )
        elif "Email" in field:
            # Special handling for known field types, e.g., Email
            input_data[field] = st.text_input(field, key=f"input_{field.lower().replace(' ', '_')}")
        elif "Phone" in field:
            input_data[field] = st.text_input(field, key=f"input_{field.lower().replace(' ', '_')}")
        elif "Birthdate (mmm/yyyy)" in field:
            input_data[field] = st.selectbox('Birth Month and Year', options=[datetime.date(year, month, 1).strftime('%b-%Y') for year in range(1950, 2024+1) for month in range(1, 13)], index=756, key=f"input_{field.lower().replace(' ', '_')}")
        else:
            input_data[field_key] = st.text_input(field, key=field_key)
      # Image upload 
    image = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'], key='file_uploader_image')
    image = st.camera_input('Take a photo', key='camera_input_image') if image is None else image
    
    submit_button = st.form_submit_button("Confirm submission")

    
if submit_button:
    # Process the image if uploaded
    st.write("Submitted data:")
    data = {'Field': [], 'Value': []}
    for key, value in input_data.items():
        data['Field'].append(key)
        data['Value'].append(value)
    df = pd.DataFrame(data)
    st.table(df)
    image_id = None
    if image is not None:
        # Assuming 'zone', 'cluster', 'first_name', 'middle_name', 'last_name' are keys in input_data
        filename = f"{input_data['selected_zone']}_{input_data['selected_cluster']}_{input_data['information_about_yourself_first_name']}_{input_data['information_about_yourself_middle_name']}_{input_data['information_about_yourself_last_name']}.jpg"
        filepath = f"./{filename}"
        with open(filepath, 'wb') as f:
            f.write(image.read())
        
        # Upload the image to Google Drive
        file_metadata = {'name': filename, 'parents': [FOLDER_ID]}
        media = MediaFileUpload(filepath, mimetype='image/jpeg')
        file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        image_id = file.get('id')
        
        st.write("Image uploaded successfully.")
        image_link = f"https://drive.google.com/uc?id={image_id}"
    else:
        image_link = "No image uploaded"
    
    # Append data to Google Sheet
    try:
        worksheet = client.open_by_key(SHEET_ID).sheet1
        row_data = [str(value) for value in input_data.values()] + [datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), image_link]
        worksheet.append_row(row_data)
        st.success("Your data has been successfully submitted!")
        st.balloons()
    except Exception as e:
        st.error(f"An error occurred: {e}")