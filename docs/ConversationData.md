# Conversation Data Formatting

This document explains how conversation data is formatted and handled in PrivacyChatBoX.

## Common Issues

When working with conversation data in a database-driven application, several issues can arise:

1. **Detached Instance Errors**: SQLAlchemy objects accessed outside their session scope throw `DetachedInstanceError`
2. **Type Inconsistency**: Some parts of the code may return model objects while others return dictionaries
3. **Attribute vs Dictionary Access**: Confusion between attribute notation (object.attribute) and dictionary notation (object["key"])

## The `format_conversation_messages` Function

The application includes a robust function for properly handling conversation data: `utils.format_conversation_messages()`

### Function Details

```python
def format_conversation_messages(messages: List) -> List[Dict[str, Any]]:
    """
    Format conversation messages for AI processing
    
    Args:
        messages: List of Message objects or message dictionaries
        
    Returns:
        List of formatted messages with attributes extracted to avoid detached instance errors,
        sorted by timestamp
    """
    formatted_messages = []
    
    for message in messages:
        try:
            # Check if the message is already a dictionary
            if isinstance(message, dict):
                # Message is already a dictionary, use it directly
                message_dict = {
                    "id": message.get('id', 0),
                    "conversation_id": message.get('conversation_id', 0),
                    "role": message.get('role', "user"),
                    "content": message.get('content', ""),
                    "timestamp": message.get('timestamp', None)
                }
            else:
                # Extract all attributes to prevent detached instance errors
                message_dict = {
                    "id": getattr(message, 'id', 0),
                    "conversation_id": getattr(message, 'conversation_id', 0),
                    "role": getattr(message, 'role', "user"),
                    "content": getattr(message, 'content', ""),
                    "timestamp": getattr(message, 'timestamp', None)
                }
            
            formatted_messages.append(message_dict)
        except Exception as e:
            # Log the error but continue processing other messages
            print(f"Error formatting message: {e}")
            continue
    
    # Sort messages by timestamp
    formatted_messages.sort(key=lambda x: x["timestamp"] if x["timestamp"] else datetime.min)
    
    return formatted_messages
```

### Key Features

1. **Type Handling**: Correctly processes both SQLAlchemy model objects and dictionaries
2. **Error Recovery**: Continues processing even if individual messages have errors
3. **Consistent Output**: Always returns a list of dictionaries in a consistent format
4. **Chronological Ordering**: Sorts messages by timestamp
5. **Default Values**: Provides sensible defaults if attributes/keys are missing

## Usage Examples

### Processing Messages from Database

```python
from utils import format_conversation_messages
from database import session_scope
from models import Message

# Get messages from database
with session_scope() as session:
    messages = session.query(Message).filter(Message.conversation_id == conversation_id).all()
    
    # Format messages to avoid detached instance errors
    formatted_messages = format_conversation_messages(messages)

# Now you can safely use formatted_messages outside the session
for message in formatted_messages:
    print(f"{message['role']}: {message['content']}")
```

### Processing Messages from API

```python
# Messages from an API might already be dictionaries
api_messages = get_messages_from_api()
formatted_messages = format_conversation_messages(api_messages)

# Use the consistently formatted messages
for message in formatted_messages:
    print(f"{message['role']}: {message['content']}")
```

### Sending to AI Providers

```python
from ai_providers import get_ai_response
from utils import format_conversation_messages

# Format messages consistently before passing to AI providers
formatted_messages = format_conversation_messages(messages)
response = get_ai_response(user_id, formatted_messages)
```

## Best Practices

1. **Always Use the Formatter**: Even if you think your data is already in the right format, using the formatter ensures consistency.

2. **Dictionary Access**: After formatting, always use dictionary access syntax:
   ```python
   # Correct
   message["content"]
   
   # Incorrect
   message.content
   ```

3. **Error Handling**: The formatter handles individual message errors, but still wrap calls in try-except for robust error handling:
   ```python
   try:
       formatted_messages = format_conversation_messages(messages)
   except Exception as e:
       print(f"Error formatting messages: {e}")
       formatted_messages = []
   ```

4. **Work Within Sessions**: When fetching from the database, always format within the session:
   ```python
   with session_scope() as session:
       messages = session.query(Message).filter(...).all()
       formatted_messages = format_conversation_messages(messages)
   
   # Now formatted_messages can be used outside the session
   ```

## Conclusion

Using the `format_conversation_messages` function consistently throughout the application ensures that conversation data is handled robustly and prevents common errors related to detached instances and inconsistent data formats.