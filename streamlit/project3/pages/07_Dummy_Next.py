import streamlit as st
import pandas as pd
import os
from PIL import Image

st.title("My dog")

current_script_dir = os.path.dirname(os.path.abspath(__file__))
streamlit_root_dir = os.path.abspath(os.path.join(current_script_dir, "../../"))
image_path = os.path.join(streamlit_root_dir, "data", "ingo.jpg")

img = Image.open(image_path)
rotated_img = img.transpose(Image.ROTATE_270) # Use Image.ROTATE_270 for 90 degrees clockwise
st.image(rotated_img, caption = 'My dog', width = 500)
