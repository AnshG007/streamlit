import streamlit as st
import os
import zipfile
import time
import subprocess

class Uploader:
    class Model:
        pageTitle = "Uploader"
        
    def __init__(self):
        self.extract_folder = None
        self.zip_folder = "temp_storage"  # Change to your desired temporary storage directory
        self.file_list = []  # List to store filenames inside the ZIP or the uploaded PDF

    def save_pdf(self, file):
        # PDF files are saved in the specified directory
        pdf_save_path = "../sparrow-data/docs/input/invoices/Dataset with valid information"
        pdf_path = os.path.join(pdf_save_path, file.name)
        os.makedirs(pdf_save_path, exist_ok=True)
        with open(pdf_path, "wb") as f:
            f.write(file.getbuffer())
        self.file_list.append(file.name)
        st.success(f"PDF file '{file.name}' saved directly to '{pdf_save_path}'")

    def extract_zip(self, file):
        # ZIP files are temporarily saved in the specified directory
        os.makedirs(self.zip_folder, exist_ok=True)
        zip_path = os.path.join(self.zip_folder, file.name)
        with open(zip_path, "wb") as f:
            f.write(file.getbuffer())
        self.file_list.extend(self.get_files_in_zip(zip_path))
        st.success(f"ZIP file '{file.name}' uploaded successfully!")

        # Extract the contents directly to the specified directory
        extract_path = "../sparrow-data/docs/input/invoices/Dataset with valid information"
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)

        # Delete the temporary ZIP file
        os.remove(zip_path)

    def get_files_in_zip(self, zip_path):
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            return zip_ref.namelist()

    def upload_file(self, file):
        if file.type == "application/pdf":
            self.save_pdf(file)
        elif file.type in ["application/zip", "application/x-zip-compressed"]:
            self.extract_zip(file)
        else:
            st.warning(f"Unsupported file format: {file.type}")

    def invoke_additional_script(self):
        # Display "Please wait" message and prevent user interaction
        wait_message = st.empty()
        #with st.spinner("Please wait..."):
            # Invoke your subprocess here
        self.run_subprocess()
        #wait_message.success("Done!")

    def run_subprocess(self):
        # Replace the following line with the actual command to invoke your Python script
        # Example: subprocess.run(["python", "your_script.py"])
        # Simulating subprocess with sleep
        subprocess.run(["python", "../sparrow-data/run_ocr.py"])
        subprocess.run(["python", "../sparrow-data/run_converter.py"])
        subprocess.run(["python", "../sparrow-data/deleteFiles.py"])
        subprocess.run(["python", "../sparrow-data/grouping.py"]+ self.file_list)
        #st.write("Additional script invoked.")

    def view(self):
        st.title("Uploader View")
        
        uploaded_file = st.file_uploader("Choose a file", type=["pdf", "zip"])

        if uploaded_file:
            st.write("File uploaded successfully!")

            # Use a spinner to indicate processing
            with st.spinner("Processing file..."):
                # Sleep for a short time to simulate processing
                #time.sleep(2)
                wait_message = st.empty()
                self.upload_file(uploaded_file)
                self.invoke_additional_script()
                wait_message.success("Done!")

            # Clear the spinner and show "Done!" once processing is complete
            st.success("Done!")

            # Display the list of filenames
            st.write("List of filenames:")
            for filename in self.file_list:
                st.write(filename)

# Instantiate and run the Uploader
