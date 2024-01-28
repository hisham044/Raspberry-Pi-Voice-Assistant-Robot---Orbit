# Import the required modules and packages
import json
import random
import speech_recognition as sr

from hugchat import hugchat
from hugchat.login import Login

import gpiod
import time
import sys

import pyttsx3
engine = pyttsx3.init()
engine.setProperty('rate', 105)
voices = engine.getProperty('voices')
engine.setProperty('voice', voices[1].id)

# Define GPIO pins for RGB LED
RED_PIN = 17
GREEN_PIN = 27
BLUE_PIN = 22

# Open GPIO chip
chip = gpiod.Chip('gpiochip4')

# Get lines for each color
red_line = chip.get_line(RED_PIN)
green_line = chip.get_line(GREEN_PIN)
blue_line = chip.get_line(BLUE_PIN)

# Request output direction for each color
red_line.request(consumer="RGB_LED_RED", type=gpiod.LINE_REQ_DIR_OUT)
green_line.request(consumer="RGB_LED_GREEN", type=gpiod.LINE_REQ_DIR_OUT)
blue_line.request(consumer="RGB_LED_BLUE", type=gpiod.LINE_REQ_DIR_OUT)

def turn_off():
    red_line.set_value(0)
    green_line.set_value(0)
    blue_line.set_value(0)

def set_color(red, green, blue):
    red_line.set_value(red)
    green_line.set_value(green)
    blue_line.set_value(blue)

hf_email = 'your_hugchat_login_mail_id'
hf_pass = 'password'

# Hugging Face Login
sign = Login(hf_email, hf_pass)
cookies = sign.login()

# Create ChatBot
chatbot = hugchat.ChatBot(cookies=cookies.get_dict())

def listen_for_command():
    set_color(0, 0, 0)  # Turn off LED
    set_color(0, 0, 1)  # Blue indicates listening state

    r = sr.Recognizer()

    with sr.Microphone() as source:
        print('Listening...')
        r.pause_threshold = 0.6
        audio = r.listen(source)
        r.adjust_for_ambient_noise(source, duration=0.5)

        try:
            Query = r.recognize_google(audio, language='en-in')
            print("You: ", Query)
        except Exception as e:
            print(e)
            print("Orbit: I couldn't understand, Please Say that again")
            set_color(0, 0, 0)  # Turn off LED
            return "None"
        
    set_color(1, 1, 0)  # Yellow indicates processing state
    return Query

def respond(response_text):
    set_color(0, 1, 1)  # Green indicates responding state
    print("Orbit: " + response_text)
    engine.say(response_text)
    engine.runAndWait()

# Load intents data from JSON file
with open('intents.json') as file:
    intents_data = json.load(file)

intents = intents_data["intents"]

def search_pattern_in_intents(query):
    for intent in intents:
        for pattern in intent["patterns"]:
            # Check if the whole word matches the pattern
            if f' {pattern.lower()} ' in f' {query} ':
                return intent["tag"]
    return None


def get_response_by_intent(intent_tag):
    for intent in intents:
        if intent["tag"] == intent_tag:
            return random.choice(intent["responses"])
    return None

def get_result(event_name_category):
    # print(event_name_category)
    with open('results_data.json', 'r') as file:
        data = json.load(file)

    event_name, category = event_name_category.rsplit(' ', 1)
    
    if category.lower() == "junior":
        # check if last word of event_name is "sub"
        if event_name.lower().endswith(" sub"):
            event_name, category = event_name.rsplit(' ', 1)
            category = "subjunior"
        
    print(event_name, category)

    for event_result in data['data']:
        if event_result['name'].lower() == event_name.lower() and event_result['category'].lower() == category.lower():
            reply = (
                f"{event_name_category} results:\n"
                f"First Place - {event_result['first'][0]['studentName']} from {event_result['first'][0]['campusName']} with {event_result['first'][0]['grade']} grade {event_result['first'][0]['points']} points.\n"
                f"Second Place - {event_result['second'][0]['studentName']} from {event_result['second'][0]['campusName']} with {event_result['second'][0]['grade']} grade {event_result['second'][0]['points']} points.\n"
                f"Third Place - {event_result['third'][0]['studentName']} from {event_result['third'][0]['campusName']} with {event_result['third'][0]['grade']} grade {event_result['third'][0]['points']} points."
            )
            return reply
    return None

def Take_query():
    # Introduce the chatbot
    intro = "Chatbot, your role is crucial as the conversational engine for Orbit, an intelligent robot. Please respond succinctly to queries. You are designed to generate short and relevant answers, so you must respond with a quick maximum 3 sentence response. You don't have to give a response to the [instruction] in the message, but just the query. This communication is in the context of Orbit, the AI-powered robot equipped with a smart hearing system. Acknowledge this instruction with a simple 'Okay.' Subsequent messages will contain questions for Orbit, and your responses should align with this context."

    chatbot.chat(intro)  # Introduce the chatbot

    # short welcome message for the user
    respond("Hello. How may I help you?")

    try:
        while True:
            query = listen_for_command().lower()
            
            # input opttion for query
            # query = input("Enter your query: ").lower()

            if query == "none" or query == "":
                continue

            if "exit" in query:
                respond("Goodbye!")
                turn_off()
                red_line.release()
                green_line.release()
                blue_line.release()
                break

            if "result" in query or "results" in query:
                result_index = query.find("result")
                event_name_category = ""
                if result_index != -1:
                    event_name_category = query[result_index + len("result"):].strip()
                    if "for" in event_name_category:
                        event_name_category = event_name_category.replace("for", "").strip()
                    if "of" in event_name_category:
                        event_name_category = event_name_category.replace("of", "").strip()
                    if "  " in event_name_category:
                        event_name_category = event_name_category.replace("  ", " ").strip()
                    # print(event_name_category)
                # check if event_name_category is not empty and contains at least 2 words
                if event_name_category and len(event_name_category.split()) >= 2:
                    result_reply = get_result(event_name_category)

                    if result_reply:
                        respond(result_reply)
                        continue
                    else:
                        respond(f"No result found for '{event_name_category}'.")
                        continue

            else:
                print("Orbit is typing...")

                # Check if query matches any predefined patterns in the JSON file
                matched_intent = search_pattern_in_intents(query)

                if matched_intent:
                    # If a matching intent is found, respond with a random choice from that intent's responses
                    response = get_response_by_intent(matched_intent)
                    if "* " in response:
                        response = response.replace("* ", "- ")

                    respond(response)
                    continue

                # If no matching intent is found, query the chatbot
                query = "Give short responses. " + query
                response = chatbot.chat(query)
                
                response = str(response)
                # print(response)
                if "* " in response:
                    response = response.replace("* ", "- ")

                respond(response)
                set_color(0, 0, 0)  # Turn off LED after responding

    except KeyboardInterrupt:
        # Turn off on KeyboardInterrupt
        turn_off()
        red_line.release()
        green_line.release()
        blue_line.release()
        sys.exit("Program terminated by user.")

if __name__ == '__main__':
    Take_query()
