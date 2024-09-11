from flask import Blueprint, render_template, request, flash, jsonify, redirect, url_for, session, current_app
from flask_login import login_required, current_user
from .models import Note
from . import db
import json
from flask_dropzone import Dropzone
import markdown2 as markdown
import os
from dotenv import load_dotenv
from openai import OpenAI
 
# Load environment variables from .env file
# load_dotenv()

# api_key = os.getenv('OPENAI_API_KEY')
api_key = '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'
client = OpenAI(api_key=api_key)

# print(api_key)

gpt = Blueprint('gpt', __name__)


@gpt.route('/aiChat')
@login_required
def aiChat():
    return render_template('aiChat.html'  , user=current_user)

import logging

@gpt.route('/chat', methods=['POST'])
@login_required
def chat_api():
    data = request.get_json()
    logging.info(f"Received data: {data}")  # Log the received data

    user_message = data.get('message')
    logging.info(f"User message: {user_message}")  # Log the user message

    # Implement your GPT logic here
    # bot_response = f"GPT response to: {user_message}"
    # return jsonify({'response': bot_response})

    # assistant = client.beta.assistants.create(
    #     name="Document Analyst & Questions Answering Assistant",
    #     instructions="""
    #         You are an expert Document Analyst. Use your documents  to answer questions  and  solve problems. Please be best at your accuracy of data extracting from the document. 

    #         if you can't give a answer correctly, please respond as "Hello, Good day. Sorry for the inconvinience. but according to you documents we can't answer this question" Could you please rewrite the question or ask another? Thank you..." 
    #         """,
    #     model="gpt-4o-mini",
    #     tools=[{"type": "file_search"}],
    # )

    #call upload funtion
    # vector_store_id=''

    assistant = client.beta.assistants.update(
        # assistant_id='asst_RY5e6di42yXB36mcHWxSFDrA',
        assistant_id=assistant_id,
        tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
    )

    # Create a thread and attach the file to the message
    thread = client.beta.threads.create(
        messages=[
            {
            "role": "user",
            "content": f"Provide accurate and summarize answers to below according to provided documents: {user_message}"
            # Attach the new file to the message if ou want prefer documentation.                    
            }
        ]
    )
    
    print(assistant.id)
    
    # The thread now has a vector store with that file in its tool resources.
    # print(thread.tool_resources.file_search)

    # Use the create and poll SDK helper to create a run and poll the status of
    # the run until it's in a terminal state.

    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id, assistant_id=assistant_id
    )

    messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))

    message_content = messages[0].content[0].text
    annotations = message_content.annotations
    citations = []
    for index, annotation in enumerate(annotations):
        message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
        if file_citation := getattr(annotation, "file_citation", None):
            cited_file = client.files.retrieve(file_citation.file_id)
            citations.append(f"[{index}] {cited_file.filename}")
            
    response = message_content.value
    citation_text = "\n".join(citations)
    print(response)
    print(citation_text)

    # Process the message (You can add your GPT or any logic here)
    # For simplicity, we'll just echo the message back
    response_message = response
    response_citation = f"<i>Source: {citation_text}</i>"

    # Convert Markdown to HTML
    response_message = markdown.markdown(response_message)

    return jsonify({
        'user_message': user_message,
        'response': response_message,
        'citation_text': response_citation
    })

@gpt.route('/chat')
@login_required
def chat():
        return render_template("chat.html" , user=current_user)


# Initialize an empty list to store file paths
uploaded_files = []

@gpt.route('/upload', methods=['POST', 'GET'])
@login_required
def upload():
    if request.method == 'POST':
        f = request.files.get('file')
        if f:
            # Save the file to the configured upload path
            file_path = os.path.join(current_app.config['UPLOADED_PATH'], f.filename)
            f.save(file_path)
            
            # Add the file path to the uploaded_files list
            uploaded_files.append(file_path)
            
            # Print the file path, content type, and filename for debugging
            # print(f"File Path: {file_path}")
            # print(f"Content Type: {f.content_type}")
            # print(f"Filename: {f.filename}")
            print(uploaded_files)

            assistant = client.beta.assistants.create(
                name="Document Analyst & Questions Answering Assistant",
                instructions="""
                    You are an expert Document Analyst. Use your documents  to answer questions  and  solve problems. Please be best at your accuracy of data extracting from the document. 

                    if you can't give a answer correctly, please respond as "Hello, Good day. Sorry for the inconvinience. but according to you documents we can't answer this question" Could you please rewrite the question or ask another? Thank you..." 
                    """,
                model="gpt-4o-mini",
                tools=[{"type": "file_search"}],
            )



            #openai vectorstore upload
            # Create a vector store caled "Financial Statements"
            vector_store = client.beta.vector_stores.create(name="Test Docs")
            
            # Ready the files for upload to OpenAI
            file_streams = [open(path, "rb") for path in uploaded_files]
            
            # Use the upload and poll SDK helper to upload the files, add them to the vector store,
            # and poll the status of the file batch for completion.
            file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
                 vector_store_id=vector_store.id, files=file_streams
            )
            
            # You can print the status and the file counts of the batch to see the result of this operation.
            print(file_batch.status)
            print(file_batch.file_counts)
            # print(vector_store)
            # print(client.beta.vector_stores.list())

            # vector_store_id='vs_wezGDuGGSoz0cKgXxh0DHPG6'

            # assistant = client.beta.assistants.update(
            #     assistant_id=assistant.id,
            #     tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}},
            # )
            print(vector_store.id)
            # print(assistant.id)
            
            global vector_store_id
            vector_store_id = vector_store.id
            global assistant_id
            assistant_id = assistant.id


    
            # # Create a thread and attach the file to the message
            # thread = client.beta.threads.create(
            #     messages=[
            #         {
            #         "role": "user",
            #         "content": f"Provide accurate and summarize answers to below according to the documents in vectorstore: {user_message}",
            #         # Attach the new file to the message if ou want prefer documentation.                    
            #         }
            #     ]
            # )
            
            # # The thread now has a vector store with that file in its tool resources.
            # print(thread.tool_resources.file_search)

            # # Use the create and poll SDK helper to create a run and poll the status of
            # # the run until it's in a terminal state.

            # run = client.beta.threads.runs.create_and_poll(
            #     thread_id=thread.id, assistant_id=assistant.id
            # )

            # messages = list(client.beta.threads.messages.list(thread_id=thread.id, run_id=run.id))

            # message_content = messages[0].content[0].text
            # annotations = message_content.annotations
            # citations = []
            # for index, annotation in enumerate(annotations):
            #     message_content.value = message_content.value.replace(annotation.text, f"[{index}]")
            #     if file_citation := getattr(annotation, "file_citation", None):
            #         cited_file = client.files.retrieve(file_citation.file_id)
            #         citations.append(f"[{index}] {cited_file.filename}")

            # # global response
            # # global citation_text
            # response = message_content.value
            # citation_text = "\n".join(citations)
            # print(response)
            # print(citation_text)

    return render_template("chat.html", user=current_user, uploaded_files=uploaded_files)









