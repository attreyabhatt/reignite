import requests
from src.conversation.utils.image_gpt import extract_conversation_from_image
from src.conversation.utils.custom_gpt import generate_custom_response

def download_file(url, save_path):
    try:
        response = requests.get(url, stream=True)  # Use stream=True for large files
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        with open(save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"File downloaded successfully to: {save_path}")

    except requests.exceptions.RequestException as e:
        print(f"Error downloading file: {e}")
    except IOError as e:
        print(f"Error saving file: {e}")

# Example usage:
file_url = "https://i.redd.it/ofzjgxbbaeif1.jpeg"  # Replace with the actual URL
local_filename = "downloaded_file.jpeg"  # Replace with your desired local filename
download_file(file_url, local_filename)
conversation = extract_conversation_from_image(local_filename)
replies = generate_custom_response(conversation,situation='stuck_after_reply',her_info='')
print(replies)
