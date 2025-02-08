import json
from flask import Flask, render_template, session, jsonify, request
from model import get_ai_response, get_conversation_data, breakers

from flask_session import Session
from decouple import config
import redis
from redis import Redis


REDIS_URL = config('REDIS_URL')
REDIS_PORT = config('REDIS_PORT')
PASSWORD = config('REDIS_PASSWORD')

app = Flask(__name__)
app.config['SECRET_KEY']= config('SECRET_KEY')
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'flask-session:'
app.config['SESSION_REDIS'] = redis.StrictRedis(host=REDIS_URL, port=REDIS_PORT, password=PASSWORD, ssl=True)
# Redis(host='localhost', port=6379)
Session(app)

def switch_to_next_prompt():
    session["prompt_queue"].pop(0)
    if session["prompt_queue"]:
        session["current_prompt"] = session["prompt_queue"][0]
        return True
    else:
        return None

def prompt_checker(prompt_name, convo_history, current_convo, ai_response):
    prompt_handlers = {
        "therapy_note": lambda: {
            "type": "convo", 
            "data": get_conversation_data(current_convo)
        },
        "session_summary": lambda: {
            "type": "convo", 
            "data": get_conversation_data(convo_history)
        },
        "set_agenda": lambda: {
            "type": "json", 
            "data": json.dumps(ai_response)
        },
        "ai_chatbot": lambda: {
            "type": "json", 
            "data": json.dumps(ai_response)
        },
        "thought_response": lambda: {
            "type": "json", 
            "data": json.dumps(
                get_ai_response(
                    prompt="problem_summary", 
                    input=f"***CONVERSATION LOG\n{get_conversation_data(current_convo)}\n***",
                    res_key="summary",
                    convo=current_convo
                )
            ),
            "breaker": "response_ready"
        },
        "provide_homework": lambda: {
            "type": "json", 
            "data": json.dumps({
                "therapy_note": session.get("note", ""),
                "activity": session.get("activity", "")
            })
        }
    }
    
    handler = prompt_handlers.get(prompt_name, lambda: {"type": None})
    return handler()

def generate_ai_response():
    input_details =  prompt_checker(
        session["current_prompt"], 
        session["conversation"], 
        session["current_convo"], 
        session["previous_response"]
    )
    if not input_details["type"]:
        response = get_ai_response(prompt=session["current_prompt"], convo=session["current_convo"])
    else:
        if input_details["type"] == "json":
            input_data = f"***JSON INPUT\n{input_details['data']}\n***"
        else:
            input_data = f"***CONVERSATION LOG\n{input_details['data']}\n***"      
        response = get_ai_response(prompt=session["current_prompt"], convo=session["current_convo"], input=input_data)
    
    return response

def update_conversation(role, content):
    conversation = session.get("conversation", [])
    current_convo = session.get("current_convo", [])
    conversation.append({"role": role, "content": content})
    current_convo.append({"role": role, "content": content})
    session["conversation"] = conversation
    session["current_convo"] = current_convo
    session.modified = True

def get_feedback_response():
    if session["feedback_messages"]:
        ai_response = session["feedback_messages"].pop(0)
        print("feedback: ", ai_response)
        update_conversation("assistant", ai_response)
        return jsonify({
            "message": ai_response,
            "feedback": "inprogress"
            })
    else:
        return jsonify({
            "feedback": "completed"
        })



@app.route("/")
def homepage():
    if not "conversation" in session:
        session["conversation"] = []
        session["current_convo"] = []
        session["note"] = ""
        session["homework"] = []
        session["activity"] = []
        session["previous_response"] = None
        session["current_prompt"] = "weekly_update"
        session["prompt_queue"] = \
        [
            "weekly_update", 
            "set_agenda", 
            "ai_chatbot", 
            "thought_response", 
            "therapy_note", 
            "provide_homework", 
            "session_summary"
        ]
        session["feedback_messages"] = ["Before we wrap up, I'd really value your thoughts on today's session. Was there anything you found especially helpful or anything you think we could approach differently next time?", "Thank you for sharing that. Your feedback is really important to me so I can better support you"]
        
        initial_message = get_ai_response(prompt=session["current_prompt"], convo=session["current_convo"])
        print(initial_message)
        update_conversation("assistant", initial_message["res"])
        return render_template("home.html", initial_message=initial_message["res"])
    return render_template("home.html", conversation=session["conversation"])


@app.route("/send_message", methods=["POST"])
def send_message():
    user_message = request.json["message"]

    if not session["prompt_queue"]:
        if session["feedback_messages"]:
            update_conversation("user", user_message)
        return get_feedback_response()

    update_conversation("user", user_message)
    ai_response = generate_ai_response()
    if not ai_response:
        session["conversation"].pop()
        session["current_convo"].pop()
        print("An error occured")
        return  jsonify({
            "error": True
        })
    
    print(session["conversation"])

    if ai_response.get(breakers.get(session["current_prompt"], "done")) == True:
        session["previous_response"] = ai_response
        if session["current_prompt"] == "therapy_note":
            session["note"] = ai_response["therapy_note"]
        elif session["current_prompt"] == "thought_response":
            if ai_response.get("suggestions", None):
                session["activity"] = [ai_response["suggestions"], ai_response["days"]]
        elif session["current_prompt"] == "provide_homework":
            if ai_response.get("homework", None):
                session["homework"] = ai_response["homework"]

        if switch_to_next_prompt() == None:
            return get_feedback_response()
            
        ai_response = generate_ai_response()
        session["current_convo"] = []
    update_conversation("assistant", ai_response["res"])

    return jsonify({
        "message": ai_response["res"],
        "feedback": "inprogress"
        })


@app.route("/get_notes")
def get_notes():
    print("Notes: ", session["note"])
    print("Homework: ", session["homework"])
    print("Activity: ", session["activity"])
    return jsonify({
        "therapy_notes": session["note"] if session["note"] else None,
        "homework": session["homework"] if session["homework"] else None
    })
 
if __name__ == "__main__":
    app.run(debug=config('DEBUG'))