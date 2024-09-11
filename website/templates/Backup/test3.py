from openai import OpenAI
 
client = OpenAI()

vector_store_id='vs_wezGDuGGSoz0cKgXxh0DHPG6'

assistant = client.beta.assistants.update(
    assistant_id='asst_RY5e6di42yXB36mcHWxSFDrA',
    tool_resources={"file_search": {"vector_store_ids": [vector_store_id]}},
)

# Create a thread and attach the file to the message
thread = client.beta.threads.create(
    messages=[
        {
        "role": "user",
        "content": f"Provide accurate and summarize answers within 50 words to the below according to the documents in vectorstore: Who is hashan?",
        # Attach the new file to the message if ou want prefer documentation.                    
        }
    ]
)

# The thread now has a vector store with that file in its tool resources.
# print(thread.tool_resources.file_search)

# Use the create and poll SDK helper to create a run and poll the status of
# the run until it's in a terminal state.

run = client.beta.threads.runs.create_and_poll(
    thread_id=thread.id, assistant_id=assistant.id
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

# global response
# global response_citation
response = message_content.value
response_citation = "\n".join(citations)
# print(message_content)
print(response)
print(response_citation)
