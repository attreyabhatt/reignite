import re

def is_left_on_read(text):
    # Regex: matches 'you' or 'her', optional spaces, colon, then message (possibly empty)
    pattern = re.compile(r'^(you|her)\s*:\s*', re.IGNORECASE)

    # Process each line, building full messages with sender
    messages = []
    current_sender = None
    current_message = ''
    for line in text.splitlines():
        if not line.strip():
            continue  # Skip blank lines

        match = pattern.match(line)
        if match:
            # Save previous message if exists
            if current_sender is not None:
                messages.append((current_sender, current_message.strip()))
            current_sender = match.group(1).lower()
            current_message = line[match.end():].strip()
        else:
            # Continuation of previous message
            current_message += '\n' + line.strip()

    # Add the last message
    if current_sender is not None:
        messages.append((current_sender, current_message.strip()))

    if not messages:
        return False

    # Check if last message is from 'you'
    return messages[-1][0] == 'you'