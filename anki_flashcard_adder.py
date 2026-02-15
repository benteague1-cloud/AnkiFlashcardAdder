#word to anki deck
# anki_flashcard_adder.py
#
# Author: Gemini, Ben
# Date: July 15, 2025

import json
import urllib.request
import os
# -- gemini 2.5 on free allows a lot fo usage at the time I made this, it's unclear if that's still the case now but other services can easily be written in and out
# --- Function to get Gemini API Key ---
def get_gemini_api_key():
    """
    Retrieves the Gemini API key from an environment variable.
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("---")
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        print("Please set the environment variable with your Gemini API key.")
        print("You can get a key from Google AI Studio.")
        print("---")
        return None
    return api_key

# --- MODIFIED: Function to generate content with Gemini for improved formatting ---
def generate_flashcard_content(api_key, concept):
    """
    Uses the Gemini API to generate a definition and an example for a given concept.
    Returns the content as a single HTML-formatted string.
    """
    print(f"\nGenerating definition and example for '{concept}' using Gemini...")
    try:
        # Construct the prompt for the Gemini API, asking for HTML formatting
        # have been meaning to update this to work better with translations, but works well for english words at least
        prompt = (
            f"You are an assistant that creates educational flashcards. "
            f"For the term '{concept}', provide a clear, concise definition and a simple, "
            f"illustrative example sentence and/or model/instance. "
            f"if the term contains an indication of a foreign language, remove the name of the language from the card title"
            f"If the definition involves multiple distinct concepts or types (like different types of engines), "
            f"please describe each in a separate HTML paragraph (`<p>`). "
            f"Format the entire response using HTML tags. "
            f"The definition should come first, followed by the example. "
            f"Ensure the example is italicized using `<i>` tags. "
            f"Do not include any JSON formatting, just the complete HTML string."
            f"if the provided concept is in quotation marks, cite the quotation as I am trying to commit this quote to memory and want to accurately remember the source"
        )

        # Prepare the data for the API request
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "response_mime_type": "text/plain", # Expecting raw HTML text now
            }
        }
        
        # Make the API request
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}
        data = json.dumps(payload).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req) as response:
            response_body = response.read().decode() # Read response body for debugging
            if response.status == 200:
                try:
                    # Parse the result to get the text content
                    result = json.loads(response_body)
                    if result.get('candidates') and len(result['candidates']) > 0 and \
                       result['candidates'][0].get('content') and \
                       result['candidates'][0]['content'].get('parts') and \
                       len(result['candidates'][0]['content']['parts']) > 0:
                        content_html = result['candidates'][0]['content']['parts'][0]['text']
                        return content_html
                    else:
                        print(f"Error: No text content found in Gemini API response. Response: {result}")
                        return None
                except json.JSONDecodeError:
                    print(f"Error: Could not decode JSON from Gemini API text response. Response body: {response_body}")
                    return None
            else:
                print(f"Error from Gemini API (text generation): Status {response.status}, Reason: {response.reason}. Response body: {response_body}")
                return None

    except urllib.error.HTTPError as http_e:
        error_body = http_e.read().decode()
        print(f"HTTP Error from Gemini API (text generation): Status {http_e.code}, Reason: {http_e.reason}. Response body: {error_body}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred while calling the Gemini API (text generation): {e}")
        return None

def anki_request(action, **params):
    """
    Helper function to make a request to the AnkiConnect API.
    """
    request_data = json.dumps({'action': action, 'version': 6, 'params': params}).encode('utf-8')
    request = urllib.request.Request('http://localhost:8765', request_data)
    try:
        response = urllib.request.urlopen(request)
        response_data = json.load(response)
        if response_data.get('error'):
            raise Exception(response_data['error'])
        return response_data.get('result')
    except Exception as e:
        print(f"Error communicating with AnkiConnect: {e}")
        print("Please ensure Anki is running and the AnkiConnect add-on is installed and configured correctly.")
        return None

def create_flashcard():
    """
    Main function to get user input and create an Anki flashcard.
    """
    print("--- AI-Powered Anki Flashcard Adder ---")

    # --- Get API Key ---
    gemini_api_key = get_gemini_api_key()
    if not gemini_api_key:
        return
    
    # 1. Get Deck Name
    try:
        deck_names = anki_request('deckNames')
        if deck_names is None: return

        print("\nAvailable Decks:")
        for name in deck_names:
            print(f"- {name}")

        #essentially "favourite deck" with simple y/n
        if input("\nAI_Adder?") == "y":
            deck_name = "AI_Adder"
        elif input("\nAI_Adder?") == "n":
            deck_name = input("\nEnter the name of the deck to add the card to: ")

        if deck_name not in deck_names:
            create_deck = input(f"Deck '{deck_name}' does not exist. Create it? (y/n): ").lower()
            if create_deck == 'y':
                if anki_request('createDeck', deck=deck_name) is None:
                    print(f"Failed to create deck '{deck_name}'.")
                    return
                print(f"Deck '{deck_name}' created successfully.")
            else:
                print("Card creation cancelled.")
                return
    except Exception as e:
        print(f"An error occurred while handling decks: {e}")
        return

    # 2. Get concept from user and generate content
    concept = input("\nEnter the word or concept for the flashcard: ")
    
    # The generated_content will now be the full HTML string
    generated_content_html = generate_flashcard_content(gemini_api_key, concept)
    if not generated_content_html:
        print("Could not generate card content. Please try again.")
        return

    front = concept
    # The 'back' field directly uses the HTML generated by Gemini
    back = generated_content_html

    tags = input("Enter tags for the card (comma-separated, optional): ").split(',')
    tags = [tag.strip() for tag in tags if tag.strip()]

    # 3. Define the note structure
    note = {
        'deckName': deck_name,
        'modelName': 'Basic', # Ensure this model exists in Anki and supports HTML
        'fields': {
            'Front': front,
            'Back': back
        },
        'options': {
            'allowDuplicate': False,
            'duplicateScope': 'deck'
        },
        'tags': tags
    }

    # 4. Add the note to Anki
    try:
        result = anki_request('addNote', note=note)
        if result:
            print(f"\nSuccessfully added card to '{deck_name}'!")
            print(f"  Front: {front}")
            print(f"  Back Content (HTML): \n{back}") # Print the full HTML for verification
            print(f"  Tags: {', '.join(tags)}")
        else:
            print("\nFailed to add the card. Check for errors above.")
    except Exception as e:
        print(f"An error occurred while adding the note: {e}")


if __name__ == '__main__':
    # --- Setup Instructions ---
    # 1. Make sure Anki is running on your computer.
    #
    # 2. Install the AnkiConnect add-on in Anki:
    #    - Go to Tools > Add-ons.
    #    - Click "Get Add-ons..." and paste the following code: 2055492159
    #    - Restart Anki.
    #
    # 3. Get a Gemini API Key:
    #    - Go to Google AI Studio (https://aistudio.google.com/) and create an API key.
    #
    # 4. Set the API Key as an Environment Variable:
    #    - For Windows: setx GEMINI_API_KEY "YOUR_GEMINI_API_KEY"
    #    - For macOS/Linux: export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
    #    - (Note: You may need to restart your terminal for the change to take effect)
    #
    # 5. Run this script from your terminal:
    #    python anki_flashcard_adder.py
    # --------------------------

    create_flashcard()

