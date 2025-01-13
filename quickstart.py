import base64
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


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
    results = service.users().messages().list(userId = "me").execute()
    messages = results.get("messages", [])

    print(len(messages))
    for message in messages:
        msg = service.users().messages().get(userId="me", id=message["id"]).execute()

        # print("PARSING MSG ID" + message["id"])
        if "parts" not in msg["payload"].keys():
            p = msg["payload"]
            data = base64.urlsafe_b64decode(msg["payload"]["body"]["data"]).decode("utf-8")
            print(data)
        else:
            for p in msg["payload"]["parts"]:
                if p["mimeType"] == "text/plain":
                    data = base64.urlsafe_b64decode(p["body"]["data"]).decode("utf-8")
                    print(data)
            
    # print(results)

    # if not labels:
    #   print("No labels found.")
    #   return
    # print("Labels:")
    # for message in messages:
    #   print(message["snippet"])

  except HttpError as error:
    # TODO(developer) - Handle errors from gmail API.
    print(f"An error occurred: {error}")


if __name__ == "__main__":
  main()