import base64
import requests
from bs4 import BeautifulSoup
import json

# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }


# --------------- Functions that control the skill's behavior ------------------

def csrf(html):
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup.find_all('input'):
        if tag.attrs['name'] == '_csrf':
            return tag.attrs['value']


def get_session():
    client_id = <client id>
    client_secret = <secret id>
    
    s = requests.Session()
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    params = {
        'response_type': 'code',
        'client_id': client_id,
        'scope': 'control_headlights read_odometer read_vehicle_info read_battery control_horn',
        'redirect_uri': 'https://www.google.com',
    }
    r = s.get('https://tesla.smartcar.com/oauth/authorize', headers=headers, params=params)
    
    payload = {
        '_csrf': csrf(r.text),
        'username': <username> ,
        'password': <password>
    }
    r = s.post('https://tesla.smartcar.com/oauth/login', headers=headers, data=payload)
    
    if 'code' in r.url:
        code = r.url[r.url.find('code') + 5:]
    else:
        payload = {
            '_csrf': csrf(r.text),
            'vehicleId': <vehicleID>,
            'approval': 'true'
        }
        r = s.post('https://tesla.smartcar.com/oauth/grant', headers=headers, data=payload)
        code = r.url[r.url.find('code') + 5:]
    
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': b'application/x-www-form-urlencoded',
    }
    payload = {
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': 'https://www.google.com',
    }
    r = s.post('https://auth.smartcar.com/oauth/token', headers=headers, data=payload, auth=requests.auth.HTTPBasicAuth(client_id, client_secret))
    
    j = json.loads(r.content)
    token = j['access_token']
    return s, token


def battery(s, token):
    headers = {
        'Authorization': 'Bearer ' + token,
    }
    r = s.get('https://api.smartcar.com/v1.0/vehicles/359abe33-8a0a-403c-a596-aa664d69e91d/battery', headers=headers)
    j = json.loads(r.text)
    percent = j['percentRemaining']
    return int(percent * 100)


def flash(s, token):
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': b'application/json',
        'Authorization': 'Bearer ' + token,
    }
    
    body = {
        'action': 'FLASH',
        'type': 'LOW_BEAM'
    }
    s.post('https://api.smartcar.com/v1.0/vehicles/359abe33-8a0a-403c-a596-aa664d69e91d/lights/headlights', headers=headers, json=body)


def honk(s, token):
    headers = {
        'User-Agent': 'Mozilla/5.0',
        'Content-Type': b'application/json',
        'Authorization': 'Bearer ' + token,
    }
    
    body = {
        'action': 'HONK'
    }
    s.post('https://api.smartcar.com/v1.0/vehicles/359abe33-8a0a-403c-a596-aa664d69e91d/horn', headers=headers, json=body)


def get_welcome_response():

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Welcome to Smart Car."
    
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    
    reprompt_text = "Please hack this Tesla."
    should_end_session = False
    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thank you for trying the Alexa Skills Kit sample. " \
                    "Have a nice day! "
    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


def battery_level(intent, session):
    s, token = get_session()
    percent = battery(s, token)
    return build_response({}, build_speechlet_response(
        intent['name'], f"The battery level is {percent} percent.", None, False))


def flash_lights(intent, session):
    s, token = get_session()
    flash(s, token)
    return build_response({}, build_speechlet_response(
        intent['name'], 'The lights are flashing.', None, False))


def honk_horn(intent, session):
    s, token = get_session()
    honk(s, token)
    return build_response({}, build_speechlet_response(
        intent['name'], 'Honk honk.', None, False))


def say_hello(intent, session):
    s, token = get_session()
    honk(s, token)
    flash(s, token)
    honk(s, token)
    flash(s, token)
    return build_response({}, build_speechlet_response(
        intent['name'], 'Hello.', None, False))

# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']

    # Dispatch to your skill's intent handlers
    if intent_name == "FlashLights":
        return flash_lights(intent, session)
    elif intent_name == "BatteryLevel":
        return battery_level(intent, session)
    elif intent_name == "HonkHorn":
        return honk_horn(intent, session)
    elif intent_name == "SayHello":
        return say_hello(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.
    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])