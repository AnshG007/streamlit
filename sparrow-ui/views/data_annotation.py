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
from st_aggrid import AgGrid
import matplotlib.pyplot as plt


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
        annotation_text = "Annotation"
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
        copy = None
        

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
            st.subheader(model.subheader_1)

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

            completed_check = st.empty()

            btn = st.button(model.export_labels_text)
            if btn:
                self.export_labels(model)
                st.write(model.done_text)

            st.subheader(model.subheader_2)

            with st.form("upload-form", clear_on_submit=True):
                uploaded_file = st.file_uploader(model.upload_button_text_desc, accept_multiple_files=False,
                                                 type=['png', 'jpg', 'jpeg'],
                                                 help=model.upload_help)
                submitted = st.form_submit_button(model.upload_button_text)

                if submitted and uploaded_file is not None:
                    ret = self.upload_file(uploaded_file)

                    if ret is not False:
                        file_names = self.get_existing_file_names('docs/images/')

                        annotation_index = self.get_annotation_index(annotation_selection, file_names)
                        annotation_selection = placeholder_upload.selectbox(model.annotation_text, file_names,
                                                                            index=annotation_index,
                                                                            help=model.annotation_selection_help)
                        st.session_state['annotation_index'] = annotation_index

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
                    tab = st.radio("Select", ["Mapping", "Grouping", "Ordering", "labelTrial", "Observation"], horizontal=True,
                                   label_visibility="collapsed")
                    if tab == "Mapping":
                        self.render_form(model, result_rects, data_processor, annotation_selection)
                    elif tab == "Grouping":
                        self.group_annotations(model, result_rects)
                    elif tab == "Ordering":
                        self.order_annotations(model, model.labels, model.groups, result_rects)
                    elif tab == "labelTrial":
                        self.labelTrial(model , result_rects,data_processor)
                    elif tab == "Observation":
                        self.observations(model)
            else:
                result_rects = self.render_doc(model, docImg, saved_state, mode, canvas_width, doc_height, doc_width)
                tab = st.radio("Select", ["Mapping", "Grouping"], horizontal=True, label_visibility="collapsed")
                if tab == "Mapping":
                    self.render_form(model, result_rects, data_processor, annotation_selection)
                else:
                    self.group_annotations(model, result_rects)
                

    def render_doc(self, model, docImg, saved_state, mode, canvas_width, doc_height, doc_width,data_processor):
        col1, col2 = st.columns(2)
        # if "visibility" not in st.session_state:
        #     st.session_state.visibility = "visible"
        #     st.session_state.disabled = False
        with st.container():
            # Retrieve words and meta from saved_state
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
                                        data_processor)

                    with toolbar:
                        submit = st.form_submit_button(model.save_text, type="primary")
                        if submit:
                            for word in result_rects.rects_data['words']:
                                if len(word['value']) > 1000:
                                    st.error(model.error_text)
                                    return

                            with open(model.rects_file, "w") as f:
                                json.dump(result_rects.rects_data, f, indent=2)
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

    def render_form_view(self, words, labels, result_rects, data_processor):
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
            key=f"ag-grid-{i}" 
        )
        rows = response['selected_rows']
        #value = response['value'].values.tolist()
        data = response['data'].values.tolist()
        #print(data[1])
                
        for i, rect in enumerate(words):
            value = data[i][1]
            label = data[i][2]

            if i == result_rects.current_rect_index:
                
                #print("Selected Box Value:", value)  # Display the value of the selected box
                #print(labels)
                #print("Selected Label:", selected_label)  # Display selected label
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


    def group_annotations(self, model, result_rects):
        with st.form(key="grouping_form"):
            if result_rects is not None:
                words = result_rects.rects_data['words']
                data = []
                for i, rect in enumerate(words):
                    data.append({'id': i, 'value': rect['value']})
                df = pd.DataFrame(data)

                formatter = {
                    'id': ('ID', {**PINLEFT, 'width': 50}),
                    'value': ('Value', PINLEFT)
                }

                toolbar = st.empty()

                response = agstyler.draw_grid(
                    df,
                    formatter=formatter,
                    fit_columns=True,
                    selection='multiple',
                    use_checkbox='True',
                    pagination_size=40
                )

                rows = response['selected_rows']

                with toolbar:
                    submit = st.form_submit_button(model.save_text, type="primary")
                    if submit and len(rows) > 0:
                        # check if there are gaps in the selected rows
                        if len(rows) > 1:
                            for i in range(len(rows) - 1):
                                if rows[i]['id'] + 1 != rows[i + 1]['id']:
                                    st.error(model.selection_must_be_continuous)
                                    return

                        words = result_rects.rects_data['words']
                        new_words_list = []
                        coords = []
                        for row in rows:
                            word_value = words[row['id']]['value']
                            rect = words[row['id']]['rect']
                            coords.append(rect)
                            new_words_list.append(word_value)
                        # convert array to string
                        new_word = " ".join(new_words_list)

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
                        for row in rows[::-1]:
                            if i == len(rows) - 1:
                                break
                            del words[row['id']]
                            i += 1

                        result_rects.rects_data['words'] = words

                        with open(model.rects_file, "w") as f:
                            json.dump(result_rects.rects_data, f, indent=2)
                        st.session_state[model.rects_file] = result_rects.rects_data
                        st.experimental_rerun()

    def labelTrial(self , model , result_rects,data_processor):

        #print(model.v)
        '''
        with st.form(key='labelTrial'):
            data =[]
            #print(result_rects.rects_data)
            #trying_list  = json.load(open(model.rects_file))
            if result_rects is not None:
                words = result_rects.rects_data['words']
                for i,rect in enumerate(words):
                    if i == result_rects.current_rect_index:
                        #print(result_rects.current_rect_index)
                        value = rect['value'] 
                        group, label = rect['label'].split(":", 1) if ":" in rect['label'] else (None, rect['label'])
                        data.append({'value': value, 'label': label})
                        #data_processor.update_rect_data(result_rects.rects_data, i, value, label)


            #print(data)          
            df = pd.DataFrame(data)
            
            #print(df)
            formatter = {
                'id': ('ID', {**PINLEFT, 'width': 50 , 'hide':True}),
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
            response = agstyler.draw_grid(
                df,
                formatter=formatter,
                fit_columns=True,
                selection='multiple',
                
                pagination_size=40,
                grid_options=go
                 
            )

            #rows = response['selected_rows']
            
            
            data = response['data'].values.tolist()
            #print(data[0][1])
            for i, rect in enumerate(words):
                
                if i == result_rects.current_rect_index:
                    rect['label'] = data[0][1]
                    
                    #print(rect['label'])
                    p = data_processor.update_rect_data(result_rects.rects_data, i, rect['value'], rect['label'])
            
            
            #print(p)
            submit = st.form_submit_button(model.save_text, type="primary")
            if submit :     
                with open(model.rects_file, "w") as f:
                    #print(result_rects.rects_data)
                    json.dump(result_rects.rects_data, f, indent=2)
                    
                    st.session_state[model.rects_file] = result_rects.rects_data
                    st.experimental_rerun()
            
       
        '''
        #Multiple selection
        
        words = result_rects.rects_data['words']
        col1 , col2 = st.columns(2)
        with col1:
            btn = st.button('Refresh', type="primary")
        with col2:
            del_button = st.button("delete",type="primary")
        
        print("**************************************************************************************")
        print(result_rects.current_rect_index)
        print(model.copy)
        print("**************************************************************************************")
        if not btn and not del_button:
            for i, rect in enumerate(words):
                if i == result_rects.current_rect_index:
                    
                    if i != model.copy:
                        model.l.append(i)
                        model.v.append(rect['value'])
                    
                        
        elif btn and not del_button:
            model.v.clear()
            model.l.clear()
            st.experimental_rerun()
            
            
        #print(model.l)
        with st.form(key='multipleLabelTrial'):   
            multiple_data = []
            custom_rect_list = []
            
            for index , rect in enumerate(words):
                for i , v in enumerate(model.l):
                    if index == v :
                        if rect['rect'] not in custom_rect_list:
                            value = rect['value'] 
                            group, label = rect['label'].split(":", 1) if ":" in rect['label'] else (None, rect['label'])
                            multiple_data.append({ 'value': value, 'label': label})
                            custom_rect_list.append(rect['rect'])
                            
                            
            dataFrame = pd.DataFrame(multiple_data)
            #edited_df = st.data_editor(dataFrame, num_rows="dynamic")
            #print(multiple_data)
            formatter = {
            'id': ('ID', {**PINLEFT, 'width': 50 }),
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
            response = agstyler.draw_grid(
                dataFrame,
                formatter=formatter,
                fit_columns=True,
                selection='multiple',
                
                pagination_size=40,
                grid_options=go
                
            )
            updated_data = response['data'].values
            #print(updated_data)
            for index, v in enumerate(model.l):
                if v < len(words):
                        rect = words[v]  # Get the rectangle corresponding to the index in model.l
                        label_index = custom_rect_list.index(rect['rect'])  # Find the index of v in model.l
                        label = updated_data[label_index][1]  # Get the corresponding label from updated_data
                        rect['label'] = label  # Update the label of the rectangle
                        #print(rect['label'])
                        p = data_processor.update_rect_data(result_rects.rects_data, v, rect['value'], rect['label'])
            submit_btn = st.form_submit_button(model.save_text, type="primary")
            if submit_btn :     
                with open(model.rects_file, "w") as f:
                    #print(result_rects.rects_data)
                    json.dump(result_rects.rects_data, f, indent=2)
                    st.session_state[model.rects_file] = result_rects.rects_data
                    st.experimental_rerun()
            #removal
        del_data = result_rects.rects_data
        print(f"model.v before the deletion button: {model.v}")
        #print(del_data)
        #print(model.l)
        #print(model.v)
        if del_button:
            #print(f"before : {len(del_data['words'])}")
            del_words = del_data['words']
            #print(del_words)
            for i, rect in enumerate(del_words):
                if i == result_rects.current_rect_index :
                    
                    if i in model.l:
                        
                        value = rect['value']
                        index = i
                        model.copy = i
                        for item in model.v:
                            if value in model.v:
                                model.v.remove(value)
                        del_words.pop(index)
                        model.l.remove(i)
                        result_rects.current_rect_index = None
                        
                        print("#####################################################################")
                        print(i)
                        print(model.l) 
                        print(model.v) 
                        print(result_rects.current_rect_index)          
                        print("#####################################################################")
            print(f"model.v after the deletion: {model.v}")             
            del_data['words'] = del_words
            #print(f"after : {len(del_data['words'])}")
            #result_rects.rects_data['words'] = del_data['words']
            with open(model.rects_file, 'w') as f:
                json.dump(del_data, f, indent=2)
                st.session_state[model.rects_file] = del_data
                st.experimental_rerun()

                
            # for i, rect in enumerate(words):
            #     value = del_data[i][1]
            #     label = del_data[i][2]

            #     if i == result_rects.current_rect_index:
            #         data_processor.update_rect_data(result_rects.rects_data, i, value, label)

            
            # if del_button:
            #     with open(model.rects_file, "w") as f:
            #         #print(result_rects.rects_data)
            #         json.dump(result_rects.rects_data, f, indent=2)
            #         st.session_state[model.rects_file] = result_rects.rects_data
            #         st.experimental_rerun()
        

    def observations(self , model):
        array = []
        with st.form(key = "observe"):
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

            
            

           
                
                
                        
                        



    def order_annotations(self, model, labels, groups, result_rects):
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