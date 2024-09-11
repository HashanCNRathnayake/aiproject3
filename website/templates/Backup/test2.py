from openai import OpenAI
# client = OpenAI()

# completion = client.chat.completions.create(
#     model="gpt-4o-mini",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant."},
#         {
#             "role": "user",
#             "content": "Write a 4 line song for praise teacher."
#         }
#     ]
# )

# print(completion.choices[0].message.content)from openai import OpenAI



####image input chat
# client = OpenAI()

# import base64
# import os

# # Get the directory of the current script
# script_dir = os.path.dirname(__file__)

# # Construct the full path
# file_path = os.path.join(script_dir, 'uploads', 'download.jpeg')

# # Load the image file
# with open(file_path, 'rb') as image_file:
#     # Encode the image to base64
#     base64_image_data = base64.b64encode(image_file.read()).decode('utf-8')

# print(base64_image_data)


# response = client.chat.completions.create(
#     model="gpt-4o",
#     messages=[
#         {
#             "role": "user",
#             "content": [
#                 {"type": "text", "text": "What's in this image?"},
#                 {
#                     "type": "image_url",
#                     "image_url": {
#                         "url":f"data:image/jpeg;base64,{base64_image_data}"
#                     }
#                 },
#             ],
#         }
#     ],
#     max_tokens=300,
# )

# print(response.choices[0].message.content)

import tkinter as tk
from tkinter import filedialog
import base64
import os
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI()

# Create a Tkinter root window (it will remain hidden)
root = tk.Tk()
root.withdraw()  # Hide the root window

# Open file dialog to select an image
file_path = filedialog.askopenfilename(
    title="Select an image file",
    filetypes=[("Image Files", "*.jpeg;*.jpg;*.png;*.gif;*.bmp")]
)

if file_path:  # Check if a file was selected
    # Load the image file
    with open(file_path, 'rb') as image_file:
        # Encode the image to base64
        base64_image_data = base64.b64encode(image_file.read()).decode('utf-8')

    print(base64_image_data)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What's in this image?"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image_data}"
                        }
                    },
                ],
            }
        ],
        max_tokens=300,
    )

    print(response.choices[0].message.content)
else:
    print("No file selected.")
