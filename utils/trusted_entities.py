def contains_trusted_entity(text):
    entities = ["isro", "nasa", "rbi", "who", "gst"]
    text = text.lower()
    return any(e in text for e in entities)
