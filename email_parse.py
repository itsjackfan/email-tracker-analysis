import base64
from email.utils import parsedate_to_datetime
import os.path
import re
import unicodedata

from bs4 import BeautifulSoup
import pandas as pd

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from openai import OpenAI
from dotenv import load_dotenv

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

def clean_text(input_text):
    soup = BeautifulSoup(input_text, 'html.parser')
    input_text = soup.get_text().strip()

    # Step 1: Replace \xa0 and other non-breaking spaces with regular spaces
    cleaned = input_text.replace("\xa0", " ")

    # Step 2: Remove excessive whitespace, newline characters, and carriage returns
    cleaned = re.sub(r"\s+", " ", cleaned)  # Collapse multiple spaces into one
    cleaned = re.sub(r"(\r\n|\n|\r)", " ", cleaned)  # Normalize line breaks

    # Step 3: Remove redundant or unnecessary patterns (like borders or separators)
    cleaned = re.sub(r"[-]{10,}", "", cleaned)  # Remove lines with dashes
    cleaned = re.sub(r"[>]{2}", "", cleaned)  # Remove double angle brackets

    # Step 4: Further cleanup for readability
    cleaned = cleaned.strip()  # Trim leading/trailing spaces

    return cleaned

def llm_parse(prompt, text):
  load_dotenv()

  client = OpenAI(
     base_url="https://openrouter.ai/api/v1",
     api_key = os.environ["GEMINI_API_KEY"]
  )
  print("Created client")

  completion = client.chat.completions.create(
     model = "google/gemini-2.0-flash-exp:free",
     messages = [
        {
           "role": "user",
           "content": [
              {
                 "type": "text",
                 "text": prompt
              },
              {
                 "type": "text",
                 "text": text
              }
           ]
        }
     ]
  )
  print("Generated")
  print(completion)

  return completion.choices[0].message.content

  
  

def main():
  """Shows basic usage of the Gmail API.
  Lists the user's Gmail labels.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)

  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    # Call the Gmail API
    service = build("gmail", "v1", credentials=creds)
    messages = []
    results = service.users().messages().list(userId = "me").execute()

    while "nextPageToken" in results.keys():
      messages = messages + results.get("messages", [])
      nextToken = results.get("nextPageToken")
      results = service.users().messages().list(userId = "me", pageToken = nextToken).execute()

    messages = messages + results.get("messages", [])

    # modified from here https://github.com/itsjackfan/email-tracker-analysis
    parsed_msgs = []

    for message in messages:
      msg = service.users().messages().get(userId='me', id=message['id']).execute()                
      email_data = msg['payload']['headers']
      for values in email_data:
          name = values['name']
          if name == 'From':
              from_name = values['value']

              if 'parts' not in msg['payload'].keys():
                try:
                  data = part['body']["data"]
                  byte_code = base64.urlsafe_b64decode(data)

                  text = byte_code.decode("utf-8")
                  parsed_msgs.append(clean_text(text))                                             
                except BaseException as error:
                      pass  
              else:
                for part in msg['payload']['parts']:
                    try:
                        data = part['body']["data"]
                        byte_code = base64.urlsafe_b64decode(data)

                        text = byte_code.decode("utf-8")
                        
                        soup = BeautifulSoup(text, 'html.parser')
                        clean_text = soup.get_text().strip()
                        parsed_msgs.append(clean_text)                                             
                    except BaseException as error:
                        pass            
    
    print(set(parsed_msgs))
    print(len(set(parsed_msgs)))

    text = "Here are the messages. The next message is indicated clearly each time." + "\n\nTHIS IS NOW THE NEXT MESSAGE.\n".join(parsed_msgs)

    prompt = """
For each email in the email data:
    Extract the timestamp of the email if possible.
    Provide a brief summary of the content of the email under "summary".

    Let the next action be "Do Nothing".

    If the subject or body is from someone else (not me, Jack Fan) and I haven't responded yet, then
        Set the next action to "Respond".

    If the email is from me and the other person hasn't responded in a few days or has follow-up words like "reminder" or "due", then
        Set the next action to "Follow Up".

    If the email is important but there is no direct action called for within the email and there is not a need to respond then
        Set the next action to "Flag for Review".

    Add the extracted details and the next action to a list:
        Include the sender's email, sender's name, timestamp, subject, and next action.

Display the list of email details and their next actions as JSON.
"""

    data = llm_parse(prompt, text)[7:-4]
    print(data.json())

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()