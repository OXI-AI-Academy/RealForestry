import streamlit as st
import sqlite3
from PIL import Image, ExifTags
import os
from datetime import datetime
import requests
import wikipedia

# Database setup
DB_PATH = "real_forestry_project.db"

def create_database():
    """Create the database tables for Trees and Images."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create Trees table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Trees (
        tree_id INTEGER PRIMARY KEY,
        species TEXT,
        year_of_plantation INTEGER,
        location TEXT,
        height REAL,
        width REAL,
        crown_size REAL,
        stem_bark_code TEXT UNIQUE,
        images TEXT,
        wikipedia_link TEXT,
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Create Images table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Images (
        image_id INTEGER PRIMARY KEY,
        collection_date DATE,
        focal_length REAL,
        height INTEGER,
        width INTEGER,
        file_path TEXT UNIQUE,
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

# Function to add image data to the database
def add_image(image_data):
    """Add image details to the Images table."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO Images (collection_date, focal_length, height, width, file_path)
    VALUES (?, ?, ?, ?, ?)
    """, image_data)
    conn.commit()
    conn.close()

# Function to identify tree species using Plant.id API
def identify_tree(image_path):
    """Send the image to the Plant.id API for identification."""
    api_key = "your_api_key_here"  # Replace with your Plant.id API key
    url = "https://api.plant.id/v2/identify"
    headers = {"Authorization": f"Bearer {api_key}"}

    with open(image_path, "rb") as image_file:
        response = requests.post(
            url,
            headers=headers,
            files={"images": image_file},
            data={"organs": "leaf"}
        )
    if response.status_code == 200:
        result = response.json()
        # Extract the most probable species name and confidence
        species = result["suggestions"][0]["plant_name"]
        confidence = result["suggestions"][0]["probability"]
        return species, confidence
    else:
        st.error(f"API request failed: {response.status_code} - {response.text}")
        return None, None

# Wikipedia function to get tree details
def get_wikipedia_details(tree_name):
    """Fetch details of the tree from Wikipedia."""
    try:
        # Add 'tree' to the search term to narrow down results
        tree_name_query = f"{tree_name} tree"
        summary = wikipedia.summary(tree_name_query, sentences=3)
        link = wikipedia.page(tree_name_query).url
        return summary, link
    except wikipedia.exceptions.DisambiguationError as e:
        st.error(f"Disambiguation error: {e}")
        return None, None
    except wikipedia.exceptions.HTTPTimeoutError:
        st.error("Wikipedia request timed out.")
        return None, None
    except wikipedia.exceptions.PageError:
        st.error(f"Page for '{tree_name}' not found. Please check the tree name.")
        return None, None

# Streamlit app
def main():
    st.title("Real Forestry Project")
    st.write("Capture tree data and save it to the database.")

    # Create the database if not already created
    create_database()

    # Step 1: Capture or upload an image
    st.header("Capture or Upload Tree Image")
    img_data = st.camera_input("Take a picture of the tree") or st.file_uploader("Or upload an image", type=["jpg", "png", "jpeg"])

    if img_data is not None:
        # Save the image locally
        img_path = os.path.join("images", f"tree_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        os.makedirs("images", exist_ok=True)
        with open(img_path, "wb") as f:
            f.write(img_data.read())

        st.success(f"Image saved: {img_path}")

        # Extract EXIF metadata
        image = Image.open(img_path)
        exif_data = {}
        if image._getexif():
            exif_data = {
                ExifTags.TAGS[key]: value
                for key, value in image._getexif().items()
                if key in ExifTags.TAGS
            }
        focal_length = exif_data.get("FocalLength", 0)
        resolution = (image.size[0], image.size[1])

        # Display image metadata
        st.write("### Image Metadata")
        st.write(f"Focal Length: {focal_length} mm")
        st.write(f"Resolution: {resolution[0]}x{resolution[1]} pixels")

        # Save metadata to the database
        image_data = (
            datetime.now().strftime("%Y-%m-%d"),  # collection_date
            focal_length,                         # focal_length
            resolution[1],                        # height
            resolution[0],                        # width
            img_path                              # file_path
        )
        add_image(image_data)
        st.success("Image metadata saved to the database.")

        # Step 2: Identify tree species automatically
        st.header("Tree Species Identification")
        species, confidence = identify_tree(img_path)

        if species:
            st.write(f"**Identified Species:** {species}")
            st.write(f"**Confidence:** {confidence * 100:.2f}%")

            # Step 3: Add tree details
            st.header("Add Tree Details")
            with st.form("tree_form"):
                year_of_plantation = st.number_input("Year of Plantation", min_value=1900, max_value=datetime.now().year, step=1)
                location = st.text_area("Location")
                height = st.number_input("Height (meters)", min_value=0.0, step=0.1)
                width = st.number_input("Width (meters)", min_value=0.0, step=0.1)
                crown_size = st.number_input("Crown Size (meters)", min_value=0.0, step=0.1)
                stem_bark_code = st.text_input("Stem Bark Code (unique)")
                wikipedia_link = st.text_input("Wikipedia Link")

                submitted = st.form_submit_button("Save Tree Data")
                if submitted:
                    tree_data = (
                        species, year_of_plantation, location, height, width, crown_size,
                        stem_bark_code, img_path, wikipedia_link
                    )
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("""
                    INSERT INTO Trees (species, year_of_plantation, location, height, width, crown_size, stem_bark_code, images, wikipedia_link)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, tree_data)
                    conn.commit()
                    conn.close()
                    st.success("Tree data saved to the database.")

    # Step 4: Manual Tree Name Entry
    st.header("Manual Tree Name Entry")
    manual_tree_name = st.text_input("Enter the tree name")

    if manual_tree_name:
        # Fetch Wikipedia details for manual tree name entry
        summary, link = get_wikipedia_details(manual_tree_name)
        if summary and link:
            st.write(f"**Tree Details:** {summary}")
            st.write(f"**Wikipedia Link:** [Click here]({link})")

if __name__ == "__main__":
    main()
