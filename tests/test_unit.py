import sys
import os
import unittest
from markupsafe import Markup

# Add the project root to sys.path so we can import filters.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from filters import render_mentions_filter

class TestFilters(unittest.TestCase):
    def test_render_mentions_basic(self):
        result = render_mentions_filter("Hello @alice")
        self.assertIsInstance(result, Markup)
        self.assertEqual(str(result), 'Hello <a href="/user/alice" class="mention-link">@alice</a>')

    def test_render_mentions_html_escaping(self):
        # Ensures that malicious HTML is escaped before mentions are parsed
        result = render_mentions_filter("Check this <script>alert(1)</script> @bob")
        self.assertEqual(
            str(result), 
            'Check this &lt;script&gt;alert(1)&lt;/script&gt; <a href="/user/bob" class="mention-link">@bob</a>'
        )

    def test_render_mentions_edge_usernames(self):
        # Usernames can contain letters, numbers, and underscores
        result = render_mentions_filter("Contact @charlie_123 or @USER_99")
        self.assertEqual(
            str(result), 
            'Contact <a href="/user/charlie_123" class="mention-link">@charlie_123</a> or <a href="/user/USER_99" class="mention-link">@USER_99</a>'
        )
        
    def test_render_mentions_multiple(self):
        result = render_mentions_filter("@alice and @bob are here")
        self.assertEqual(
            str(result),
            '<a href="/user/alice" class="mention-link">@alice</a> and <a href="/user/bob" class="mention-link">@bob</a> are here'
        )

if __name__ == '__main__':
    unittest.main()
