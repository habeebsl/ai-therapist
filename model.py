import os
import json

from decouple import config
from mistralai import Mistral

api_key = config('MISTRAL_KEY')
model = "mistral-large-2411"
client = Mistral(api_key=api_key)

breakers = {"ai_chatbot": "automatic_thought", "thought_response": "response_ready", "therapy_note": "note_available"}

def get_conversation_data(convos):
    conversation_data = ""
    for convo in convos:
        role = convo["role"]
        content = convo["content"]
        prefix = "You" if role == "assistant" else "Patient"
        if conversation_data:
            conversation_data += f"\n{prefix}: {content}"
        else:
            conversation_data += f"{prefix}: {content}"
    return conversation_data

def is_only_tabs(string):
    return all(char == '\t' for char in string)

# Retrieves the json object from the raw response
def get_response(chat_response):
    count = 0
    for choice in chat_response:
        content = choice.message.content.strip()
        count += 1

        if is_only_tabs(content):
            print(f"choice {count} is only tabs")
            continue

        try:
            parsed_content = json.loads(content)
            if parsed_content == "" or parsed_content == {} or parsed_content == []:
                continue
            print(content)
            return content
        except json.JSONDecodeError:
            continue

    print("No valid JSON content found.")
    return None

# For testing purposes only
def chat_with_ai(prompt, res_key, c_input=None):
    conversation = None
    with open(os.path.join(r"prompts/", f"{prompt}.txt"), "r", encoding="utf-8") as file:
        post = file.read()

    if c_input:
        content = f"{c_input}\n\n\n{post}"
    else:
        content = f"{post}"

    messages = [
        {
            "role": "system",
            "content": content,
        }
    ]

    while True:
        chat_response = client.chat.complete(
            model = model,
            n=2,
            messages = messages,
            response_format = {
                "type": "json_object",
            }
        )

        response = json.loads(get_response(chat_response.choices))
        res = response[res_key]
        messages.append({"role": "assistant", "content": f"{res}"})
        if conversation == None:
            conversation = f"You: {res}"
        else:
            conversation += f"\nYou: {res}"
        
        if response["done"] == True:
            return response, conversation
        else:
            print(res)
            user_input = input("Say Something: ")
            messages.append({"role": "user", "content": f"{user_input}"})
            conversation += f"\nPatient: {user_input}"
        

# Main function
def get_ai_response(prompt, convo, res_key=None, input=None):
    with open(os.path.join(r"prompts/", f"{prompt}.txt"), "r", encoding="utf-8") as file:
        post = file.read()

    content = f"{input}\n\n\n{post}" if input else post

    messages = [
        {
            "role": "system",
            "content": content,
        }
    ] + convo

    print(messages)
    try:
        chat_response = client.chat.complete(
            model = model,
            n=2,
            messages = messages,
            response_format = {
                "type": "json_object",
            }
        )

        raw_response = get_response(chat_response.choices)
        print(chat_response.choices)
        print("Raw response: ", raw_response)

        if raw_response:
            response = json.loads(raw_response)
            return response
    except json.JSONDecodeError as e:
        print(f"JSON decoding error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

    return None


if __name__ == "__main__":
    topres = chat_with_ai("set_agenda", "res", json.dumps({
        "res": "Thank you for sharing. We’ve covered both your concerns and positive moments from the week. Let's move on to setting the agenda for the session.",
        "problem": ["Missed a couple classes", "I have no friends"],
        "positive": "I played some football this week, and had a lot of fun",
        "done": True
    }))

