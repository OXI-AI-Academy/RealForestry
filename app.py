import streamlit as st
import sqlite3
from PIL import Image, ImageDraw
from datetime import datetime
import wikipedia
import os

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
        bounding_box TEXT,
        created DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()

def detect_tree_and_draw_bbox(image_path):
    """Detect the tree in the image and draw a bounding box."""
    # Replace with an actual detection model for better results
    bbox = [20, 20, 250, 450]  # Mocked bounding box
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)
    draw.rectangle(bbox, outline="red", width=3)
    output_path = image_path.replace(".jpg", "_bbox.jpg")
    image.save(output_path)
    return bbox, output_path

def calculate_tree_dimensions(bbox, focal_length, img_width, img_height):
    """Calculate tree dimensions based on bounding box and image metadata."""
    sensor_width = 36.0  # mm (standard full-frame sensor width)
    distance_to_tree = 5000.0  # mm (arbitrary distance to the tree)

    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]

    tree_width = (bbox_width / img_width) * (sensor_width / focal_length) * distance_to_tree
    tree_height = (bbox_height / img_height) * (sensor_width / focal_length) * distance_to_tree
    crown_size = tree_width * 0.6  # Assume crown size is 60% of tree width

    return round(tree_height / 1000, 2), round(tree_width / 1000, 2), round(crown_size / 1000, 2)

def get_wikipedia_details(tree_name):
    """Fetch details of the tree from Wikipedia."""
    try:
        tree_name_query = f"{tree_name} tree"
        search_results = wikipedia.search(tree_name_query)
        if not search_results:
            return None, None

        page_title = search_results[0]
        summary = wikipedia.summary(page_title, sentences=3)
        link = wikipedia.page(page_title).url
        return summary, link
    except:
        return None, None

def add_tree_to_database(tree_data):
    """Add tree details to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO Trees (species, year_of_plantation, location, height, width, crown_size, stem_bark_code, images, wikipedia_link)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tree_data)
    conn.commit()
    conn.close()

def add_image_to_database(image_data):
    """Add image details to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO Images (collection_date, focal_length, height, width, file_path, bounding_box)
    VALUES (?, ?, ?, ?, ?, ?)
    """, image_data)
    conn.commit()
    conn.close()

def main():
    st.title("Real Forestry Project")
    st.write("Capture tree data and save it to the database.")

    create_database()

    st.header("Capture or Upload Tree Image")
    img_data = st.camera_input("Take a picture of the tree") or st.file_uploader("Or upload an image", type=["jpg", "png", "jpeg"])

    if img_data:
        img_path = os.path.join("images", f"tree_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg")
        os.makedirs("images", exist_ok=True)
        with open(img_path, "wb") as f:
            f.write(img_data.read())
        st.success(f"Image saved: {img_path}")

        bounding_box, bbox_img_path = detect_tree_and_draw_bbox(img_path)
        st.image(bbox_img_path, caption="Tree with Bounding Box")

        image = Image.open(img_path)
        focal_length = 50.0
        tree_height, tree_width, crown_size = calculate_tree_dimensions(bounding_box, focal_length, *image.size)
        st.write(f"Tree Height: {tree_height} meters")
        st.write(f"Tree Width: {tree_width} meters")
        st.write(f"Crown Size: {crown_size} meters")

        add_image_to_database((datetime.now().date(), focal_length, *image.size, img_path, str(bounding_box)))

    st.header("Provide Tree Details")
    species = st.text_input("Enter the tree species:")
    if st.button("Save to Database"):
        summary, wiki_link = get_wikipedia_details(species)
        tree_data = (
            species,
            datetime.now().year,
            "Unknown Location",
            tree_height,
            tree_width,
            crown_size,
            f"Stem{datetime.now().strftime('%Y%m%d%H%M%S')}",
            bbox_img_path,
            wiki_link
        )
        add_tree_to_database(tree_data)
        st.success("Tree data saved.")
        if summary:
            st.write("### Wikipedia Information")
            st.write(summary)
            st.write(f"[Read more on Wikipedia]({wiki_link})")

if __name__ == "__main__":
    main()
