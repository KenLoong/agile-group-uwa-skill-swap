import re
import markupsafe

def render_mentions_filter(text):
    """
    Convert @username in text to clickable profile links.
    Ensures HTML safety by escaping the input text before processing.
    """
    if text is None:
        return ""
    safe = str(markupsafe.escape(text))
    linked = re.sub(
        r'@(\w+)',
        r'<a href="/user/\1" class="mention-link">@\1</a>',
        safe,
    )
    return markupsafe.Markup(linked)
