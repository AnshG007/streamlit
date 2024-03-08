import subprocess
import streamlit as st
from PIL import Image
import streamlit_nested_layout
from streamlit_sparrow_labeling import st_sparrow_labeling
from streamlit_sparrow_labeling import DataProcessor
import json
import math
import os
from natsort import natsorted
from tools import agstyler
from tools.agstyler import PINLEFT
import pandas as pd
from toolbar_main import component_toolbar_main
from st_aggrid import AgGrid, GridOptionsBuilder
import matplotlib.pyplot as plt
import numpy as np



class DataAnnotation:
    class Model:
        pageTitle = "Data Annotation"

        img_file = None
        rects_file = None
        key_file = None
        labels_file = "docs/labels.json"
        groups_file = "docs/groups.json"
        

        assign_labels_text = "Assign Labels"
        text_caption_1 = "Check 'Assign Labels' to enable editing of labels and values, move and resize the boxes to annotate the document."
        text_caption_2 = "Add annotations by clicking and dragging on the document, when 'Assign Labels' is unchecked."

        labels = ["", "invoice_no", "invoice_date", "seller", "client", "seller_tax_id", "client_tax_id", "iban", "item_desc",
                  "item_qty", "item_net_price", "item_net_worth", "item_vat", "item_gross_worth", "total_net_worth", "total_vat",
                  "total_gross_worth"]

        groups = ["", "items_row1", "items_row2", "items_row3", "items_row4", "items_row5", "items_row6", "items_row7",
                  "items_row8", "items_row9", "items_row10", "summary"]

        selected_field = "Selected Field: "
        save_text = "Save"
        saved_text = "Saved!"

        subheader_1 = "Select"
        subheader_2 = "Upload"
        annotation_text = "Annotation's File Names"
        no_annotation_file = "No annotation file selected"
        no_annotation_mapping = "Please annotate the document. Uncheck 'Assign Labels' and draw new annotations"

        download_text = "Download"
        download_hint = "Download the annotated structure in JSON format"

        annotation_selection_help = "Select an annotation file to load"
        upload_help = "Upload a file to annotate"
        upload_button_text = "Upload"
        upload_button_text_desc = "Choose a file"

        assign_labels_text = "Assign Labels"
        assign_labels_help = "Check to enable editing of labels and values"

        export_labels_text = "Export Labels"
        export_labels_help = "Create key-value pairs for the labels in JSON format"
        done_text = "Done"

        grouping_id = "ID"
        grouping_value = "Value"

        completed_text = "Completed"
        completed_help = "Check to mark the annotation as completed"

        error_text = "Value is too long. Please shorten it."
        selection_must_be_continuous = "Please select continuous rows"
        l = []
        v = []
        
        rect_list = []
        indexes = []
        valuesAtIndex = []
        list_of_rect =[]
        bbox_ids = []
        

    def view(self, model, ui_width, device_type, device_width):
        with open(model.labels_file, "r") as f:
            labels_json = json.load(f)

        labels_list = labels_json["labels"]
        labels = ['']
        
        for label in labels_list:
            labels.append(label['name'])
        model.labels = labels
        #print(model.labels)
        with open(model.groups_file, "r") as f:
            groups_json = json.load(f)

        groups_list = groups_json["groups"]
        groups = ['']
        for group in groups_list:
            groups.append(group['name'])
        model.groups = groups

        with st.sidebar:
            st.markdown("---")
            #st.subheader(model.subheader_1)

            placeholder_upload = st.empty()

            file_names = self.get_existing_file_names('docs/images/')

            if 'annotation_index' not in st.session_state:
                st.session_state['annotation_index'] = 0
                annotation_index = 0
            else:
                annotation_index = st.session_state['annotation_index']

            annotation_selection = placeholder_upload.selectbox(model.annotation_text, file_names,
                                                                index=annotation_index,
                                                                help=model.annotation_selection_help)

            annotation_index = self.get_annotation_index(annotation_selection, file_names)

            file_extension = self.get_file_extension(annotation_selection, 'docs/images/')
            model.img_file = f"docs/images/{annotation_selection}" + file_extension
            model.rects_file = f"docs/json/{annotation_selection}.json"
            model.key_file = f"docs/json/key/{annotation_selection}.json"

            # print(f"before render doc {model.img_file}")
            # print(f"before render doc {model.rects_file}")

            completed_check = st.empty()

            btn = st.button(model.export_labels_text)
            if btn:
                self.export_labels(model)
                st.write(model.done_text)

            # st.subheader(model.subheader_2)

            # with st.form("upload-form", clear_on_submit=True):
            #     uploaded_file = st.file_uploader(model.upload_button_text_desc, accept_multiple_files=False,
            #                                      type=['png', 'jpg', 'jpeg'],
            #                                      help=model.upload_help)
            #     submitted = st.form_submit_button(model.upload_button_text)

            #     if submitted and uploaded_file is not None:
            #         ret = self.upload_file(uploaded_file)

            #         if ret is not False:
            #             file_names = self.get_existing_file_names('docs/images/')

            #             annotation_index = self.get_annotation_index(annotation_selection, file_names)
            #             annotation_selection = placeholder_upload.selectbox(model.annotation_text, file_names,
            #                                                                 index=annotation_index,
            #                                                                 help=model.annotation_selection_help)
            #             st.session_state['annotation_index'] = annotation_index

        # st.title(model.pageTitle + " - " + annotation_selection)
       
        

        if model.img_file is None:
            st.caption(model.no_annotation_file)
            return

        saved_state = self.fetch_annotations(model.rects_file)

        # annotation file has been changed
        if annotation_index != st.session_state['annotation_index']:
            annotation_v = saved_state['meta']['version']
            if annotation_v == "v0.1":
                st.session_state["annotation_done"] = False
            else:
                st.session_state["annotation_done"] = True
        # store the annotation file index
        st.session_state['annotation_index'] = annotation_index

        # first load
        if "annotation_done" not in st.session_state:
            annotation_v = saved_state['meta']['version']
            if annotation_v == "v0.1":
                st.session_state["annotation_done"] = False
            else:
                st.session_state["annotation_done"] = True

        with completed_check:
            annotation_done = st.checkbox(model.completed_text, help=model.completed_help, key="annotation_done")
            if annotation_done:
                saved_state['meta']['version'] = "v1.0"
            else:
                saved_state['meta']['version'] = "v0.1"

            with open(model.rects_file, "w") as f:
                json.dump(saved_state, f, indent=2)
            st.session_state[model.rects_file] = saved_state

        assign_labels = st.checkbox(model.assign_labels_text, True, help=model.assign_labels_help)
        mode = "transform" if assign_labels else "rect"
        
        docImg = Image.open(model.img_file)

        data_processor = DataProcessor()

        with st.container():
            doc_height = saved_state['meta']['image_size']['height']
            doc_width = saved_state['meta']['image_size']['width']
            canvas_width, number_of_columns = self.canvas_available_width(ui_width, doc_width, device_type,
                                                                          device_width)

            if number_of_columns > 1:
                col1, col2 = st.columns([number_of_columns, 10 - number_of_columns])
                with col1:
                    result_rects = self.render_doc(model, docImg, saved_state, mode, canvas_width, doc_height, doc_width,data_processor)
                with col2:
                    tab = st.radio("Select", ["Mapping","Selected Grouping" , "Review"], horizontal=True,
                                   label_visibility="collapsed")
                    
                    # if tab == "Selected":
                    #     self.labelTrial(model , result_rects,data_processor)
                    if tab == "Mapping":
                        self.render_form(model, result_rects, data_processor, annotation_selection)
                    # elif tab == "Grouping":
                        # self.group_annotations(model, result_rects)
                    elif tab == "Selected Grouping":
                        self.SelectedGrouping(model, result_rects, data_processor)
                    # elif tab == "Ordering":
                    #     self.order_annotations(model, model.labels, model.groups, result_rects)
                    
                    elif tab == "Review":
                        self.observations(model ,result_rects)
            else:
                result_rects = self.render_doc(model, docImg, saved_state, mode, canvas_width, doc_height, doc_width,data_processor)
                tab = st.radio("Select", ["Mapping", "Grouping"], horizontal=True, label_visibility="collapsed")
                if tab == "Mapping":
                    self.render_form(model, result_rects, data_processor, annotation_selection)
                else:
                    self.group_annotations(model, result_rects)
                

    def render_doc(self, model, docImg, saved_state, mode, canvas_width, doc_height, doc_width, data_processor):
        with st.container():
           
            # Retrieve annotation index and current invoice index from session state
            if 'annotation_index' not in st.session_state:
                st.session_state['annotation_index'] = 0
            if 'invoice_index' not in st.session_state:
                st.session_state['invoice_index'] = 0
            if 'button_clicked' not in st.session_state:
                st.session_state['button_clicked'] = False

            annotation_index = st.session_state['annotation_index']
            invoice_index = st.session_state['invoice_index']

            # Retrieve list of filenames
            l = []
            for i in self.get_existing_file_names('docs/images/'):
                extension = self.get_file_extension(i, 'docs/images/')
                full_file_name = i + extension
                l.append(full_file_name)
            # pdf_files_without_full_name = []
            # for item, value in enumerate(l):

            #     value_result1 , value_result2 = value.split('.',1)
            #     value_result3 = value_result2[:-4]
            #     if value_result1 not in pdf_files_without_full_name:
                    
            #         pdf_files_without_full_name.append(value_result1)
            # #print(pdf_files_without_full_name)
            # pdf_files_with_full_name = []
            
            # for item, value in enumerate(l):
            #     value_result1 , value_result2 = value.split('.',1)
            #     value_result3 = value_result2[:-4]
            #     print(value_result1)
            #     if value_result1 in pdf_files_without_full_name:
            #         value_result4 = value_result1 + '.' + value_result3
            #         pdf_files_with_full_name.append(value_result4)
            # #print(pdf_files_with_full_name)




            # Get the current filename
            t = model.img_file.split('/')
            fileName = t[2]
            result = fileName.split('.',1)[0]

            #next_button = st.button("Next Invoice")

             # Pages of the same invoice
            rem = []
            same_invoice_pages = []
            #same_invoice_pages = [value for value in l if value.split('.', 1)[0] == result]
            for item, value in enumerate(l):
                value_result = value.split('.',1)[0]
                #value_result_2 = value.split('.',2)
                
                if value_result == result:
                    same_invoice_pages.append(value)
                else:
                    if value_result not in rem:
                        rem.append(value_result)

            remaining_files = []
            for item, value in enumerate(l):
                value_result1 , value_result2 = value.split('.',1)
                value_result3 = value_result2[:-4]
                if value_result1 in rem:
                    value_result4 = value_result1 + '.' + value_result3
                    remaining_files.append(value_result4)

            st.write('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
            

            selected_page_index = st.radio("Select Page", range(len(same_invoice_pages)), key="selectbox1")


            if selected_page_index != annotation_index:
                print("hello world")
                annotation_index = selected_page_index
                
                st.session_state['annotation_index'] = annotation_index
                st.session_state['selected_page_index'] = selected_page_index
                selected_page = same_invoice_pages[selected_page_index]
                selected_page_json = selected_page[:-4]
                
                model.img_file = f"docs/images/{selected_page}"
                model.rects_file = f"docs/json/{selected_page_json}.json"
                print(f"select box ke andar {model.img_file}")
                print(f"select box ke andar {model.rects_file}")    
                
            
            if st.button("Next Invoice"):
                st.session_state['button_clicked'] = True
                current_index = l.index(fileName)
                index = (len(same_invoice_pages) - selected_page_index  + len(l[:current_index]))
                print(selected_page_index)
                if index < len(l):
                    # if invoice_index < len(remaining_files):
                    #next_invoice_name = f"{remaining_files[invoice_index]}.jpg"
                    next_invoice_name = l[index]
                    print(next_invoice_name)
                    #next_invoice_index = l.index(next_invoice_name)
                    next_invoice_json = l[index][:-4]
                    
                    model.img_file = f"docs/images/{next_invoice_name}"
                    model.rects_file = f"docs/json/{next_invoice_json}.json"
                    st.session_state['annotation_index'] = index
                    # print(f"next button ke andar {model.img_file}")
                    # print(f"next button  ke andar {model.rects_file}")
                    
                    
                else:
                    index = 0
                    next_invoice_name = l[index]
                    print(next_invoice_name)
                    #next_invoice_index = l.index(next_invoice_name)
                    next_invoice_json = l[index]
                    #print(next_invoice_json)
                    st.session_state['annotation_index'] = index
                    model.img_file = f"docs/images/{next_invoice_name}"
                    model.rects_file = f"docs/json/{next_invoice_json}.json"
            

            if st.session_state['button_clicked']:
                st.session_state['button_clicked'] = False       

            words = saved_state.get('words', [])
            meta_info = saved_state.get('meta', {})

            # Sort words based on y-coordinate of the bbox
            words = sorted(words, key=lambda x: x['rect']['y1'])
            
            # Create a new initial_rects dictionary
            initial_rects = {
                'words': words,
                'meta': {
                    'version': meta_info.get('version', 'v0.1'),
                    'split': meta_info.get('split', 'train'),
                    'image_id': meta_info.get('image_id', 1),
                    'image_size': {
                        'width': doc_width,
                        'height': doc_height
                    }
                }
            }

            result_rects = st_sparrow_labeling(
                fill_color="rgba(0, 151, 255, 0.3)",
                stroke_width=2,
                stroke_color="rgba(0, 50, 255, 0.7)",
                background_image=docImg,
                initial_rects=initial_rects,  # Use the modified initial_rects here
                height=doc_height,
                width=doc_width,
                drawing_mode=mode,
                display_toolbar=True,
                update_streamlit=True,
                canvas_width=canvas_width,
                doc_height=doc_height,
                doc_width=doc_width,
                image_rescale=True,
                key="doc_annotation" + model.img_file
            )
            st.caption(model.text_caption_1)
            st.caption(model.text_caption_2)
        
            return result_rects  # Return after processing all words


    def render_form(self, model, result_rects, data_processor, annotation_selection):
        css = '''
                <style>
                    section.main>div {
                        padding-bottom: 1rem;
                    }
                    [data-testid="stHorizontalBlock"] {
                        display: flex;
                    }
                    [data-testid="stHorizontalBlock"]>div:first-child {
                        flex: 20 0 auto;
                        width: 50%; /* Adjust the width as needed */
                    }
                    [data-testid="stHorizontalBlock"]>div:last-child {
                        overflow: auto;
                        height: 80vh; /* Adjust the height as needed */
                    }
                    .custom-button {
                        margin-left: 0.5rem; /* Adjust the margin as needed */
                    }
                </style>
                '''

        st.markdown(css, unsafe_allow_html=True)
        with st.container():
            run_subprocess_button = st.button("Run Subprocess")
            if run_subprocess_button:
                print("HELLO")
                print(model.rects_file)
                subprocess.run(["python", "../sparrow-data/try.py", model.rects_file])
                updated_data = json.load(open(model.rects_file))
                print("world")
                # with open(model.rects_file, "w") as f:
                #     json.dump(result_rects.rects_data, f, indent=2)
                
                # Update the Streamlit app's state with the modified data
                st.session_state[model.rects_file] = updated_data
                st.experimental_rerun()
            
            if result_rects is not None:
                
                with st.form(key="fields_form"):
                    
                    toolbar = st.empty()
                    
                    self.render_form_view(result_rects.rects_data['words'], model.labels, result_rects,
                                        data_processor,model)

                    with toolbar:
                        submit = st.form_submit_button(model.save_text, type="primary")
                        if submit:
                            for word in result_rects.rects_data['words']:
                                if len(word['value']) > 1000:
                                    st.error(model.error_text)
                                    return

                            with open(model.rects_file, "w") as f:
                                print("###################################################")
                                print("hello")
                                print("###################################################")
                                json.dump(result_rects.rects_data, f, indent=2)
                                print(result_rects.rects_data)
                            st.session_state[model.rects_file] = result_rects.rects_data
                            # st.write(model.saved_text)
                            st.experimental_rerun()
                        
                       

                # Add a new button that runs a subprocess
                
                   
                if len(result_rects.rects_data['words']) == 0:
                    st.caption(model.no_annotation_mapping)
                    return
                else:
                    with open(model.rects_file, 'rb') as file:
                        st.download_button(label=model.download_text,
                                            data=file,
                                            file_name=annotation_selection + ".json",
                                            mime='application/json',
                                            help=model.download_hint)

    def render_form_view(self, words, labels, result_rects, data_processor, model):
        data = []
        for i, rect in enumerate(words):
            group, label = rect['label'].split(":", 1) if ":" in rect['label'] else (None, rect['label'])
            
            data.append({'id': i, 'value': rect['value'], 'label': label})
        df = pd.DataFrame(data)
        #print(result_rects)
        formatter = {
            'id': ('ID', {**PINLEFT, 'hide': True}),
            'value': ('Value', {**PINLEFT, 'editable': True}),
            'label': ('Label', {**PINLEFT,
                                'width': 80,
                                'editable': True,
                                'cellEditor': 'agSelectCellEditor',
                                'cellEditorParams': {
                                    'values': labels
                                }})
        }

        go = {
            'rowClassRules': {
                'row-selected': 'data.id === ' + str(result_rects.current_rect_index)
            }
        }

        green_light = "#abf7b1"
        css = {
            '.row-selected': {
                'background-color': f'{green_light} !important'
            }
        }

        response = agstyler.draw_grid(
            df,
            formatter=formatter,
            fit_columns=True,
            grid_options=go,
            css=css,
            #key=f"ag-grid" 
        )
        rows = response['selected_rows']
        #value = response['value'].values.tolist()
        data = response['data'].values.tolist()
        #print(data[1])
                
        for i, rect in enumerate(words):
            value = data[i][1]
            label = data[i][2]
            data_processor.update_rect_data(result_rects.rects_data, i, value, label)


    def canvas_available_width(self, ui_width, doc_width, device_type, device_width):
        doc_width_pct = (doc_width * 100) / ui_width
        if doc_width_pct < 45:
            canvas_width_pct = 37
        elif doc_width_pct < 55:
            canvas_width_pct = 49
        else:
            canvas_width_pct = 60

        if ui_width > 700 and canvas_width_pct == 37 and device_type == "desktop":
            return math.floor(canvas_width_pct * ui_width / 100), 4
        elif ui_width > 700 and canvas_width_pct == 49 and device_type == "desktop":
            return math.floor(canvas_width_pct * ui_width / 100), 5
        elif ui_width > 700 and canvas_width_pct == 60 and device_type == "desktop":
            return math.floor(canvas_width_pct * ui_width / 100), 6
        else:
            if device_type == "desktop":
                ui_width = device_width - math.floor((device_width * 22) / 100)
            elif device_type == "mobile":
                ui_width = device_width - math.floor((device_width * 13) / 100)
            return ui_width, 1

    def fetch_annotations(self, rects_file):
        for key in st.session_state:
            if key.startswith("docs/json/") and key != rects_file:
                del st.session_state[key]

        if rects_file not in st.session_state:
            with open(rects_file, "r") as f:
                saved_state = json.load(f)
                st.session_state[rects_file] = saved_state
        else:
            saved_state = st.session_state[rects_file]

        return saved_state
        
    def upload_file(self, uploaded_file):
        if uploaded_file is not None:
            if os.path.exists(os.path.join("docs/images/", uploaded_file.name)):
                st.write("File already exists")
                return False

            if len(uploaded_file.name) > 100:
                st.write("File name too long")
                return False

            with open(os.path.join("docs/images/", uploaded_file.name), "wb") as f:
                f.write(uploaded_file.getbuffer())

            img_file = Image.open(os.path.join("docs/images/", uploaded_file.name))

            annotations_json = {
                "meta": {
                    "version": "v0.1",
                    "split": "train",
                    "image_id": len(self.get_existing_file_names("docs/images/")),
                    "image_size": {
                        "width": img_file.width,
                        "height": img_file.height
                    }
                },
                "words": []
            }

            file_name = uploaded_file.name.split(".")[0]
            with open(os.path.join("docs/json/", file_name + ".json"), "w") as f:
                json.dump(annotations_json, f, indent=2)

            st.success("File uploaded successfully")
            

    def get_existing_file_names(self, dir_name):
        # get ordered list of files without file extension, excluding hidden files
        return natsorted([os.path.splitext(f)[0] for f in os.listdir(dir_name) if not f.startswith('.')])

    def get_file_extension(self, file_name, dir_name):
        # get list of files, excluding hidden files
        files = [f for f in os.listdir(dir_name) if not f.startswith('.')]
        for f in files:
            if file_name is not  None and os.path.splitext(f)[0] == file_name:
                return os.path.splitext(f)[1]

    def get_annotation_index(self, file, files_list):
        return files_list.index(file)


    # def group_annotations(self, model, result_rects):
    #     with st.form(key="grouping_form"):
    #         if result_rects is not None:
    #             words = result_rects.rects_data['words']
    #             data = []
    #             for i, rect in enumerate(words):
    #                 data.append({'id': i, 'value': rect['value']})
    #             df = pd.DataFrame(data)

    #             formatter = {
    #                 'id': ('ID', {**PINLEFT, 'width': 50}),
    #                 'value': ('Value', PINLEFT)
    #             }

    #             toolbar = st.empty()

    #             response = agstyler.draw_grid(
    #                 df,
    #                 formatter=formatter,
    #                 fit_columns=True,
    #                 selection='multiple',
    #                 use_checkbox='True',
    #                 pagination_size=40
    #             )

    #             rows = response['selected_rows']

    #             with toolbar:
    #                 submit = st.form_submit_button(model.save_text, type="primary")
    #                 if submit and len(rows) > 0:
    #                     # check if there are gaps in the selected rows
    #                     # if len(rows) > 1:
    #                     #     for i in range(len(rows) - 1):
    #                     #         if rows[i]['id'] + 1 != rows[i + 1]['id']:
    #                     #             st.error(model.selection_must_be_continuous)
    #                     #             return

    #                     words = result_rects.rects_data['words']
    #                     new_words_list = []
    #                     coords = []
    #                     for row in rows:
    #                         word_value = words[row['id']]['value']
    #                         rect = words[row['id']]['rect']
    #                         coords.append(rect)
    #                         new_words_list.append(word_value)
    #                     # convert array to string
    #                     new_word = " ".join(new_words_list)

    #                     # Get min x1 value from coords array
    #                     x1_min = min([coord['x1'] for coord in coords])
    #                     y1_min = min([coord['y1'] for coord in coords])
    #                     x2_max = max([coord['x2'] for coord in coords])
    #                     y2_max = max([coord['y2'] for coord in coords])


    #                     words[rows[0]['id']]['value'] = new_word
    #                     words[rows[0]['id']]['rect'] = {
    #                         "x1": x1_min,
    #                         "y1": y1_min,
    #                         "x2": x2_max,
    #                         "y2": y2_max
    #                     }

    #                     # loop array in reverse order and remove selected entries
    #                     i = 0
    #                     for row in rows[::-1]:
    #                         if i == len(rows) - 1:
    #                             break
    #                         del words[row['id']]
    #                         i += 1

    #                     result_rects.rects_data['words'] = words

    #                     with open(model.rects_file, "w") as f:
    #                         json.dump(result_rects.rects_data, f, indent=2)
    #                     st.session_state[model.rects_file] = result_rects.rects_data
    #                     st.experimental_rerun()

    def SelectedGrouping(self, model, result_rects,data_processor):
       # print(model.indexes)
        # check = st.checkbox("active")
        # Define a function to execute JavaScript code
        col1 , col2 , col3,col4 = st.columns(4)
        if 'click' not in st.session_state:
            st.session_state['click'] = False
        with col1:
            refresh = st.button("Refresh")
        with col2:
            save_label = st.button("Save Label", type="secondary") 
        with col3:
            run_subprocess_button = st.button("Auto Label")
            if run_subprocess_button:
                    print(result_rects.rects_data)
                    print("HELLO")
                    #print(model.rects_file)
                    subprocess.run(["python", "../sparrow-data/try.py", model.rects_file])
                    updated_data = json.load(open(model.rects_file))
                    print("world")
                    # with open(model.rects_file, "w") as f:
                    #     json.dump(result_rects.rects_data, f, indent=2)
                    # print("********************************************")
                    # print(updated_data)
                    # print("********************************************")
                    # Update the Streamlit app's state with the modified data
                    st.session_state[model.rects_file] = updated_data
                    st.experimental_rerun()
        with col4:
            auto_ordering = st.button("Auto order")

        
        if refresh:
            model.valuesAtIndex.clear()
            model.indexes.clear()
            model.list_of_rect.clear()
            del result_rects.current_rect_index
        with st.form(key="grouping"):

            if result_rects is not None:
                words = result_rects.rects_data['words']
                data = []
                seen_ids = set()
                for i, rect in enumerate(words):
                        if i == result_rects.current_rect_index:
                            if rect['rect'] not in model.list_of_rect:
                                    model.indexes.append(i)
                                    model.valuesAtIndex.append(rect['value'])
                                    model.list_of_rect.append(rect['rect'])
                                    #model.bbox_ids.append(i)
                                
                        
                      
                print(model.valuesAtIndex)
                print(model.indexes)

                            # else:
                            #     model.valuesAtIndex.clear()
                            #     model.indexes.clear()
                            #     model.list_of_rect.clear()
                            #     del result_rects.current_rect_index
                #df = pd.DataFrame(data)
                #print(model.valuesAtIndex)
                custom_rect_list = []
                
                for index , rect in enumerate(words):
                    for i , v in enumerate(model.indexes):
                        if index == v :
                            if rect['rect'] not in custom_rect_list:
                                id_value = index
                                value = rect['value'] 
                                group, label = rect['label'].split(":", 1) if ":" in rect['label'] else ("", rect['label'])
                                # # #print(label)
                                # if ":" in group:
                                #     group.replace(":","")
                                
                                custom_rect_list.append(rect['rect'])
                                if id_value not in seen_ids:
                                    data.append({'id': id_value, 'value': value, 'label': label, 'group': group})
                                    seen_ids.add(id_value)
                                #data.append({'id':index , 'value': value ,'label':label , 'group':group})
                #print(custom_rect_list)
                df = pd.DataFrame(data)
                sorted_list = sorted(model.indexes)
                if sorted_list == model.indexes: 
                    df = pd.DataFrame(data)
                

                # Create a dictionary with values from model.valuesAtIndex as keys and corresponding DataFrame rows as values
                else:
                    data_dict = {}
                    for value in model.valuesAtIndex:
                        data_dict[value] = df.loc[df['value'] == value]

                    # Reconstruct DataFrame with rows in the desired order
                    try:
                        df = pd.concat(data_dict.values())
                    except:
                        pass
                # try :
                #     filtered_dfs = []

                #     # Filter DataFrame rows based on the values in model.valuesAtIndex
                #     for value in model.valuesAtIndex:
                #         filtered_df = df[df['value'] == value]
                #         filtered_dfs.append(filtered_df)

                #     # Concatenate filtered DataFrames to reconstruct DataFrame with rows in the desired order
                #     df = pd.concat(filtered_dfs)

                #     print(df)

                    
                # except:
                    #pass
                formatter = {
                'id': ('ID', {**PINLEFT, 'width': 50}),
                'value': ('Value',{**PINLEFT , 'editable': True}),
                'label': ('Label', {**PINLEFT,
                                'width': 80,
                                'editable': True,
                                'cellEditor': 'agSelectCellEditor',
                                'cellEditorParams': {
                                    'values': model.labels
                                }}),
                'group': ('Group', {**PINLEFT,
                                    'width': 80,
                                    'editable': True,
                                    'cellEditor': 'agSelectCellEditor',
                                    'cellEditorParams': {
                                        'values': model.groups
                                    }})
                }

                toolbar = st.empty()

                response = agstyler.draw_grid(
                    df,
                    formatter=formatter,
                    fit_columns=True,
                    selection='multiple',
                    use_checkbox='True',
                    pagination_size=40,
                    
                    
                )
                
                rows = response['selected_rows']
                # data = response['data'].values.tolist()
                # print(data)  
                    
                 

                submit_btn = st.form_submit_button("save", type="primary")
                    
                if len(rows)>0:
                    # check if there are gaps in the selected rows
                    # if len(rows) > 1:
                    #     for i in range(len(rows) - 1):
                    #         if rows[i]['id'] + 1 != rows[i + 1]['id']:
                    #             st.error(model.selection_must_be_continuous)
                    #             return

                    words = result_rects.rects_data['words']
                    new_words_list = []
                    coords = []
                    rem_value = []
                    for row in rows:
                        word_value = words[row['id']]['value']
                        rect = words[row['id']]['rect']
                        coords.append(rect)
                        new_words_list.append(word_value)
                    # convert array to string
                    new_word = " ".join(new_words_list)
                    rem_value.append(new_word)
                    # if "new_word" not in st.session_state:
                    #     st.session_state["new_words"] = rem_value

                    # Get min x1 value from coords array
                    x1_min = min([coord['x1'] for coord in coords])
                    y1_min = min([coord['y1'] for coord in coords])
                    x2_max = max([coord['x2'] for coord in coords])
                    y2_max = max([coord['y2'] for coord in coords])


                    words[rows[0]['id']]['value'] = new_word
                    words[rows[0]['id']]['rect'] = {
                        "x1": x1_min,
                        "y1": y1_min,
                        "x2": x2_max,
                        "y2": y2_max
                    }
                    
                    # loop array in reverse order and remove selected entries
                    i = 0
                    max_value = 0
                    min_value = float('inf')
                    for row in rows[::-1]:
                        
                        if i == len(rows) - 1:

                            break
                        del words[row['id']]
                        i += 1
                    
                    # for item in model.valuesAtIndex:
                    #     if item == new_word:
                    #         pass
                    #     else:
                    #         model.valuesAtIndex.remove(item)
                    
                    for row in rows:
                        #print(f"row id {row['id']}")
                        if max_value < row['id']:
                            max_value = row['id']
                    for row in rows:
                        if row['id']<min_value:
                            min_value = row['id']
                        
                    for index in model.indexes:
                        if index == max_value:
                            model.indexes.remove(index)
                    for value in model.valuesAtIndex:
                        if value != words[min_value].get('value'):
                            model.valuesAtIndex.clear()
                            result_rects.current_rect_index = None
                    model.valuesAtIndex.append(words[min_value].get('value'))
                    # print("************************************")

                    # print(result_rects.rects_data)
                    # print("************************************")

                    print(min_value)
                    #print(f"row_id {rows[0]['id']}")
                    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")
                    print(f"valuesatIndex list {model.valuesAtIndex}")
                    print(f"indexs {model.indexes}")
                    print(f"words of min value , combined value{words[min_value]}")
                    print("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@")

                    
                    # for index, v in enumerate(model.indexes):
                    #     if v < len(words):
                    #             rect = words[min_value]  # Get the rectangle corresponding to the index 
                    #             print(rect)
                    
                    if submit_btn  and len(rows) > 0 :
                        
                        with open(model.rects_file, "w") as f:
                            json.dump(result_rects.rects_data, f, indent=2)
                        st.session_state[model.rects_file] = result_rects.rects_data
                        st.experimental_rerun()
                    
                labelled = ""          
                if save_label :
                    data = response['data'].values.tolist()
                    print(data)  
                    for index in model.indexes:
                        # Find the index of the current index in the model.indexes list
                        index_in_model = model.indexes.index(index)
                        
                        # Get the corresponding data for the current index
                        value = data[index_in_model][1]
                        label = data[index_in_model][2]
                        
                        grouping = data[index_in_model][3]
                        if grouping != "":
                            labelled = f"{grouping}:{label}"
                        else:
                            labelled = label
                        
                        #Update the rect data using the index
                        data_processor.update_rect_data(result_rects.rects_data, index, value, labelled) 

                    # Update rects data file
                    with open(model.rects_file, "w") as f:
                        json.dump(result_rects.rects_data, f, indent=2)
                    st.session_state[model.rects_file] = result_rects.rects_data
                    st.experimental_rerun()
                
                    
                if auto_ordering:
                    
                    data = response['data'].values.tolist()
                    for elem in data:
                        if elem[3] != "":
                            idx = elem[0]
                            group = elem[3]
                            words[idx]['label'] = f"{group}:{elem[2]}"


                    result_rects.rects_data['words'] = words

                    with open(model.rects_file, "w") as f:
                        json.dump(result_rects.rects_data, f, indent=2)
                    subprocess.run(["python", "../sparrow-data/jai.py", model.rects_file])

                    updated_data = json.load(open(model.rects_file))
                        
                        # Update the Streamlit app's state with the modified data
                    st.session_state[model.rects_file] = updated_data
                    st.experimental_rerun()
               
                # if save_label:
                #     data = response['data'].values.tolist()
                #     #print(words[24])
                #     print(data)
                    
                #     for i, rect in enumerate(words):
                            
                            
                #         value = data[0][1]
                #         label = data[0][2]
                                
                #         data_processor.update_rect_data(result_rects.rects_data, data[0][0], value, label) 
                    
                #     with open(model.rects_file, "w") as f:
                #         json.dump(result_rects.rects_data, f, indent=2)
                #     st.session_state[model.rects_file] = result_rects.rects_data
                #     st.experimental_rerun()


    def labelTrial(self , model , result_rects,data_processor):

        #Run subprocess button
        with st.container():
            run_subprocess_button = st.button("Run Subprocess")
            if run_subprocess_button:
                
                subprocess.run(["python", "../sparrow-data/try.py", model.rects_file])
                updated_data = json.load(open(model.rects_file))
                
                # with open(model.rects_file, "w") as f:
                #     json.dump(result_rects.rects_data, f, indent=2)
                
                # Update the Streamlit app's state with the modified data
                st.session_state[model.rects_file] = updated_data
                st.experimental_rerun()

        
        #Multiple selection
        # del_data = result_rects.rects_data
        # del_button = st.button("Delete")
        # if del_button:
        #     #print(f"before : {len(del_data['words'])}")
        #     del_words = del_data['words']
        #     #print(del_words)
        #     for i, rect in enumerate(del_words):
        #         if i == result_rects.current_rect_index :
                    
        #             if i in model.l:
                        
        #                 value = rect['value']
        #                 index = i
        #                 model.copy = i
        #                 for item in model.v:
        #                     if value in model.v:
        #                         model.v.remove(value)
        #                 del_words.pop(index)
        #                 model.l.remove(i)
        #                 result_rects.current_rect_index = None
                        
        #                 print("#####################################################################")
        #                 print(i)
        #                 print(model.l) 
        #                 print(model.v) 
        #                 print(result_rects.current_rect_index)          
        #                 print("#####################################################################")
        #     print(f"model.v after the deletion: {model.v}")             
        #     del_data['words'] = del_words
        #     #print(f"after : {len(del_data['words'])}")
        #     #result_rects.rects_data['words'] = del_data['words']
        #     with open(model.rects_file, 'w') as f:
        #         json.dump(del_data, f, indent=2)
        #     st.session_state[model.rects_file] = del_data
        #     print("rerun just begin to work")
        #     st.experimental_rerun()
            
        toolbar = st.empty()
        with toolbar:
            words = result_rects.rects_data['words']
            btn = st.button('Refresh', type="primary")
            print("**************************************************************************************")
            print(result_rects.current_rect_index)
            # print(model.copy)
            print("**************************************************************************************")
            if btn :
                model.v.clear()
                model.l.clear()
                model.rect_list.clear()
            for i, rect in enumerate(words):
                if i == result_rects.current_rect_index:
                    if rect['rect'] not in model.rect_list:
                        model.l.append(i)
                        model.v.append(rect['value'])
                        model.rect_list.append(rect['rect'])
                    
            # elif btn and not del_button:
            #     model.v.clear()
            #     model.l.clear()
            #     model.rect_list.clear()
            #     st.experimental_rerun()

        with st.form(key='multipleLabelTrial'): 
            col1,col2  = st.columns(2)  
            
            multiple_data = []
            custom_rect_list = []
            
            for index , rect in enumerate(words):
                for i , v in enumerate(model.l):
                    if index == v :
                        if rect['rect'] not in custom_rect_list:
                            value = rect['value'] 
                            group, label = rect['label'].split(":", 1) if ":" in rect['label'] else (None, rect['label'])
                            #print(label)
                            multiple_data.append({ 'value': value, 'label': label})
                            custom_rect_list.append(rect['rect'])
                            
                            
            dataFrame = pd.DataFrame(multiple_data)
            #print(multiple_data)
            
            formatter = {
            'id': ('ID', {**PINLEFT, 'width': 50,'hide':True }),
            'value': ('Value', PINLEFT),
            'label': ('Label', {**PINLEFT,
                            'width': 80,
                            'editable': True,
                            'cellEditor': 'agSelectCellEditor',
                            'cellEditorParams': {
                                'values': model.labels
                            }})
            }
            
            go = {
                'rowClassRules': {
                    'row-selected': 'data.id === ' + str(result_rects.current_rect_index)
                }
            }
            green_light = "#abf7b1"
            css = {
                '.row-selected': {
                    'background-color': f'{green_light} !important'
                }
            }
            response = agstyler.draw_grid(
                dataFrame,
                formatter=formatter,
                fit_columns=True,
                selection='multiple',
                
                pagination_size=40,
                grid_options=go,
                css = css
                
            )
            
            updated_data = response['data'].values
            
            for index, v in enumerate(model.l):
                if v < len(words):
                        rect = words[v]  # Get the rectangle corresponding to the index in model.l
                        label_index = custom_rect_list.index(rect['rect'])  # Find the index of v in model.l
                        label = updated_data[label_index][1]  # Get the corresponding label from updated_data
                        rect['label'] = label  # Update the label of the rectangle
                        #print(rect['label'])
                        p = data_processor.update_rect_data(result_rects.rects_data, v, rect['value'], rect['label'])
            with col1:
                submit_btn = st.form_submit_button(model.save_text, type="primary")
            if submit_btn :     
                with open(model.rects_file, "w") as f:
                    #print(result_rects.rects_data)
                    json.dump(result_rects.rects_data, f, indent=2)
                    st.session_state[model.rects_file] = result_rects.rects_data
                st.experimental_rerun()


    def observations(self , model,result_rects):
        sorted_list = []
        #with st.form(key = "observe"):
        '''
        file_path = model.key_file
        with open(file_path , 'r') as file:
            data = json.load(file)
        st.write("Headers")
        headers_data = data['header']
        st.write(pd.DataFrame(headers_data , [1]))
        st.write("Items")
        data_items = data['items']
        st.write(pd.DataFrame(data_items))
        form_btn = st.form_submit_button("save" , disabled=True)
        '''
        
        sorted_list = ['lineNumber', 'productCode', 'productName', 'productDesc', 'orderedQuantity', 'backOrderedQuantity', 'shippedQuantity', 'unitPrice', 'amount']
        sorted_list_header=['invoiceDate','invoiceNumber','salesOrderNumber','poNumber']

        list_of_file_names = []
        for i in self.get_existing_file_names('docs/images/'):
            extension = self.get_file_extension(i, 'docs/images/')
            full_file_name = i + extension
            list_of_file_names.append(full_file_name)
        #print(list_of_file_names)
        t = model.img_file.split('/')
        current_file_name = t[2]
        current_file_RemoveExtension = current_file_name.split('.',1)[0]

        same_invoice_page_list = []
        for item, value in enumerate(list_of_file_names):
                value_result = value.split('.',1)[0]
                #value_result_2 = value.split('.',2)
                
                if value_result == current_file_RemoveExtension:
                    same_invoice_page_list.append(value)
        #print(same_invoice_page_list)        
        
        current_file_index = list_of_file_names.index(current_file_name)
        #print(current_file_index)
        if current_file_index != 0:
            previous_file_index = current_file_index-1
            previous_file_name = list_of_file_names[previous_file_index]
            print(previous_file_name)
            if previous_file_name.endswith('.jpg'):
                remove_jpg = previous_file_name[:-4]
            
            # print(model.rects_file)
            data = None
            path = rf"docs/json/{remove_jpg}.json"
            
            with open(path , 'r' , encoding='utf-8') as json_data:
                data = json.load(json_data)
                #st.experimental_rerun()
                    
            previous_file_words = []
            
            previous_rects = []
            previous_values = []
            previous_labels=[]
            
            for rect in data['words']:
                previous_rects.append(rect.get('rect'))
                previous_values.append(rect.get('value'))
                previous_labels.append(rect.get('label'))

            for re , va , la in zip(previous_rects , previous_values , previous_labels):
                previous_file_words.append({'rect':re , 'value':va , 'label':la})
            
            

        try :
            #print(result_rects.rects_data['words'])
            rects = []
            values = []
            labels=[]
            words = []
            for rect in result_rects.rects_data['words']:
                rects.append(rect.get('rect'))
                values.append(rect.get('value'))
                labels.append(rect.get('label'))

            for r , v , l in zip(rects , values , labels):
                words.append({'rect':r , 'value':v , 'label':l})
            #print(words)
            seen_combinations = set()
            seen_labels = set()
            seen_head_label = set()
            # Create an empty dictionary to hold data for each column
            table_data = {col: [] for col in sorted_list}
            header_data = {col: [None] for col in sorted_list_header}
            
            for rect in words:
                group, label = rect['label'].split(":", 1) if ":" in rect['label'] else (None, rect['label'])
                
                extract_int = None
                
                if group is not None and group[-1].isdigit():  # Check if the last character is a digit
                    if len(group) >= 2 and group[-2].isdigit():  # Check if the second to last character is also a digit
                        extract_int = int(group[-2:])  # Extract the last two characters as an integer
                        #print(extract_int)
                    else:
                        extract_int = int(group[-1])
                    #extract_int = extract_int - 1
                    
                    
                if label != "":
                    if (label, extract_int) not in seen_combinations:
                        seen_combinations.add((label, extract_int))
                        for col in sorted_list:
                            if label == col:
                                # Append the value to the corresponding column in the table_data dictionary based on the row number
                                if extract_int is not None:
                                    max_length = max(len(table_data[col]), extract_int)
                                    table_data[col] += [None] * (max_length - len(table_data[col]))  # Fill in None for preceding rows
                                    table_data[col][extract_int - 1] = rect['value'] 
                        
                    
                        if label not in seen_labels:
                            seen_labels.add(label)
                            for col_head in sorted_list_header:
                                if label == col_head:
                                    header_data[col_head][0] = rect['value']
                                    
            #values = set()
            # Convert header_data to DataFrame
            # if same_invoice_page_list.index(current_file_name) == 0:
               
            head_df = pd.DataFrame(header_data)
            
            
            head_df_filtered = head_df.dropna(axis=1, how='all')

            
            #st.session_state['cached_df'] = head_df_filtered
            
            st.write(head_df_filtered)
            # else:
               
            #     for i, rect in enumerate(previous_file_words):
            #         group, label = rect['label'].split(":", 1) if ":" in rect['label'] else (None, rect['label'])
            #         if label != "":
            #             print(label)  # Debugging
            #             if label not in seen_labels:  # Assuming seen_labels contains all unique labels
            #                 seen_labels.add(label)
            #                 for current_rect in words:
            #                     if current_rect['value'] == rect['value']:
            #                         current_rect['label'] = f"{group}:{label}"
                                   
            #                         print(current_rect['value'], current_rect['label'])
                                    
            #                         result_rects.rects_data['words'] = words
            #                         #print(result_rects.rects_data)

            #                         # Write the updated rect data to the JSON file
            #                         with open(model.rects_file, "w") as f:
            #                             json.dump(result_rects.rects_data, f, indent=2)
            #                         st.session_state[model.rects_file] = result_rects.rects_data
            #                         st.experimental_rerun()

                #making the dataframe of header labels
                # for index , cur_rect in enumerate(words):
                #      groupped, labelled = cur_rect['label'].split(":", 1) if ":" in cur_rect['label'] else (None, cur_rect['label'])
                #      if labelled not in seen_head_label:
                #             seen_head_label.add(labelled)
                #             for col_head in sorted_list_header:
                #                 if labelled == col_head:
                #                     header_data[col_head][0] = cur_rect['value']
                # head_data_df =  pd.DataFrame(header_data)
 
                # head_df_filter = head_data_df.dropna(axis=1, how='all')
                # st.write(head_df_filter)
                # print(head_df_filter)
                              

            # Fill missing values with None if any column lengths are different
            max_length = max(len(values) for values in table_data.values())
            for col in table_data:
                table_data[col] += [None] * (max_length - len(table_data[col]))

            # Convert the dictionary to a DataFrame
            df = pd.DataFrame(table_data)
            df_filtered = df.dropna(axis=1, how='all')
            df_filtered.index = np.arange(1 , len(df_filtered)+1)
            edited_df = st.experimental_data_editor(df_filtered, num_rows= "dynamic")
            # grid = AgGrid(
            #     df.head(50),
            #     gridOptions=GridOptionsBuilder.from_dataframe(df_filtered).build(),
            # )
            #st.write(df_filtered)
            #print(edited_df)
            # User input for rows to swap
            rect1 = []
            rect2 = []
            swap_row1 = st.number_input("Enter row 1 :", min_value=1, max_value=len(df), value=1)
            swap_row2 = st.number_input("Enter row 2 :", min_value=1, max_value=len(df), value=1)
            for i , rect in enumerate(words):
                #print(rect)
                grouping, labelling = rect['label'].split(":", 1) if ":" in rect['label'] else (None, rect['label'])
            
                if grouping is not None and grouping == f"items_row{swap_row1}":
                    rect1.append(rect)
                    
                if grouping is not None and grouping == f"items_row{swap_row2}":
                    rect2.append(rect)
            # print("********&&&&&&&&&&&&")
            # print(rect1[0]['label'])
            # print("********&&&&&&&&&&&&$$$$$$$$$$$$$$")
            # print(rect2) 
            group1 = rect1[0]['label'].split(":")[0] if rect1 else None
            group2 = rect2[0]['label'].split(":")[0] if rect2 else None 
            

            # print("*******************")
            # print(f"group1 :{group1}") 
            # print(f"group1 :{group2}")
            # print("*******************")
            #swapping whole row
            for rect in rect1:
                grouping, label = rect['label'].split(":", 1) if ":" in rect['label'] else (None, rect['label'])
                if grouping:
                    rect['label'] = f"{group2}:{label}"
                    #print(f"rect of row1 :{rect['value']} {rect['label']}")

            for rect in rect2:
                grouping, label = rect['label'].split(":", 1) if ":" in rect['label'] else (None, rect['label'])
                if grouping:
                    rect['label'] = f"{group1}:{label}"
                    #print(f"rect of row2 : {rect['value']} {rect['label']} ")
                    
            
            if st.button("Swap Rows"):
                with open(model.rects_file, "w") as f:
                    json.dump(result_rects.rects_data, f, indent=2)
                    st.session_state[model.rects_file] = result_rects.rects_data
                    st.experimental_rerun()
        except:
            pass
            
        
            

    def order_annotations(self, model, labels, groups, result_rects):
        with st.container():
            run_subprocess_button = st.button("Run Subprocess")
            if run_subprocess_button:
                print("HELLO")
                subprocess.run(["python", "../sparrow-data/try.py", model.rects_file])
                updated_data = json.load(open(model.rects_file))
                print("world")
                # with open(model.rects_file, "w") as f:
                #     json.dump(result_rects.rects_data, f, indent=2)
                
                # Update the Streamlit app's state with the modified data
                st.session_state[model.rects_file] = updated_data
                st.experimental_rerun()
        if result_rects is not None:
            self.action_event = None
            data = []
            idx_list = [""]
            #updated = json.load(open(model.rects_file))
            words = result_rects.rects_data['words']
            for i, rect in enumerate(words):
                if rect['label'] != "":
                    # split string into two variables, assign None to first variable if no split is found
                    group, label = rect['label'].split(":", 1) if ":" in rect['label'] else (None, rect['label'])
                    data.append({'id': i, 'value': rect['value'], 'label': label, 'group': group})
                    idx_list.append(i)
            df = pd.DataFrame(data)

            formatter = {
                'id': ('ID', {**PINLEFT, 'width': 50}),
                'value': ('Value', {**PINLEFT}),
                'label': ('Label', {**PINLEFT,
                                    'width': 80,
                                    'editable': False,
                                    'cellEditor': 'agSelectCellEditor',
                                    'cellEditorParams': {
                                        'values': labels
                                    }}),
                'group': ('Group', {**PINLEFT,
                                    'width': 80,
                                    'editable': True,
                                    'cellEditor': 'agSelectCellEditor',
                                    'cellEditorParams': {
                                        'values': groups
                                    }})
            }

            go = {
                'rowClassRules': {
                    'row-selected': 'data.id === ' + str(result_rects.current_rect_index)
                }
            }

            green_light = "#abf7b1"
            css = {
                '.row-selected': {
                    'background-color': f'{green_light} !important'
                }
            }

            idx_option = st.selectbox('Select row to move into', idx_list)

            def run_component(props):
                value = component_toolbar_main(key='toolbar_main', **props)
                return value

            def handle_event(value):
                if value is not None:
                    if 'action_timestamp' not in st.session_state:
                        self.action_event = value['action']
                        st.session_state['action_timestamp'] = value['timestamp']
                    else:
                        if st.session_state['action_timestamp'] != value['timestamp']:
                            self.action_event = value['action']
                            st.session_state['action_timestamp'] = value['timestamp']
                        else:
                            self.action_event = None

            props = {
                'buttons': {
                    'up': {
                        'disabled': False,
                        'rendered': ''
                    },
                    'down': {
                        'disabled': False,
                        'rendered': ''
                    },
                    'save': {
                        'disabled': False,
                        'rendered': ''
                        # 'rendered': 'none',
                    }
                }
            }

            handle_event(run_component(props))

            response = agstyler.draw_grid(
                df,
                formatter=formatter,
                fit_columns=True,
                grid_options=go,
                css=css
            )

            rows = response['selected_rows']
            if len(rows) == 0 and result_rects.current_rect_index > -1:
                for i, row in enumerate(data):
                    if row['id'] == result_rects.current_rect_index:
                        rows = [
                            {
                                '_selectedRowNodeInfo': {
                                    'nodeRowIndex': i
                                },
                                'id': row['id']
                            }
                        ]
                        break

            if str(self.action_event) == 'up':
                if len(rows) > 0:
                    idx = rows[0]['_selectedRowNodeInfo']['nodeRowIndex']
                    if idx > 0:
                        row_id = rows[0]['id']
                        if row_id == idx_option:
                            return
                        # swap row upwards in the array
                        if idx_option == "":
                            words[row_id], words[row_id - 1] = words[row_id - 1], words[row_id]
                        else:
                            for i in range(1000):
                                words[row_id], words[row_id - 1] = words[row_id - 1], words[row_id]
                                row_id -= 1
                                if row_id == idx_option:
                                    break

                        result_rects.rects_data['words'] = words

                        with open(model.rects_file, "w") as f:
                            json.dump(result_rects.rects_data, f, indent=2)
                        st.session_state[model.rects_file] = result_rects.rects_data
                        st.experimental_rerun()
            elif str(self.action_event) == 'down':
                if len(rows) > 0:
                    idx = rows[0]['_selectedRowNodeInfo']['nodeRowIndex']
                    if idx < len(df) - 1:
                        row_id = rows[0]['id']
                        if row_id == idx_option:
                            return
                        # swap row downwards in the array
                        if idx_option == "":
                            words[row_id], words[row_id + 1] = words[row_id + 1], words[row_id]
                        else:
                            for i in range(1000):
                                words[row_id], words[row_id + 1] = words[row_id + 1], words[row_id]
                                row_id += 1
                                if row_id == idx_option:
                                    break

                        result_rects.rects_data['words'] = words

                        with open(model.rects_file, "w") as f:
                            json.dump(result_rects.rects_data, f, indent=2)
                        st.session_state[model.rects_file] = result_rects.rects_data
                        st.experimental_rerun()
            elif str(self.action_event) == 'save':
                data = response['data'].values.tolist()
                for elem in data:
                    if elem[3] != "None":
                        idx = elem[0]
                        group = elem[3]
                        words[idx]['label'] = f"{group}:{elem[2]}"


                result_rects.rects_data['words'] = words

                with open(model.rects_file, "w") as f:
                    json.dump(result_rects.rects_data, f, indent=2)
                subprocess.run(["python", "../sparrow-data/jai.py", model.rects_file])

                updated_data = json.load(open(model.rects_file))
                    
                    # Update the Streamlit app's state with the modified data
                st.session_state[model.rects_file] = updated_data
                st.experimental_rerun()
                

    def export_labels(self, model):
        path_from = os.path.join("docs/json/")
        path_to = os.path.join("docs/json/key/")

        files = [f for f in os.listdir(path_from) if not f.startswith('.')]
        for file in files:
            path = os.path.join(path_from, file)
            if os.path.isfile(path):
                with open(path, "r") as f:
                    data = json.load(f)
                    words = data['words']

                    keys = {}
                    row_keys = {}

                    for word in words:
                        if word['label'] != '':
                            if ':' in word['label']:
                                group, label = word['label'].split(':', 1)
                                if 'row' not in group:
                                    if group not in keys:
                                        keys[group] = {}
                                    keys[group][label] = word['value']
                                else:
                                    if "items" not in keys:
                                        keys["items"] = []

                                    if group not in row_keys:
                                        row_keys[group] = {}
                                    row_keys[group][label] = word['value']
                            else:
                                keys[word['label']] = word['value']

                    if row_keys != {}:
                        for key in row_keys:
                            keys["items"].append(row_keys[key])

                    if keys != {}:
                        path = os.path.join(path_to, file)
                        with open(path, "w") as f:
                            json.dump(keys, f, indent=2)