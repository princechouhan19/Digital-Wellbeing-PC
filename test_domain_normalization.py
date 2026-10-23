import pytest

def test_normalize_domain():
    # Since FocusManager needs a repo, let's just create one manually
    from database.repository import Repository
    from protection.focus_manager import FocusManager
    
    # We can use the singleton if we want, but better to instantiate isolated
    repo = Repository()
    fm = FocusManager(repo)
    
    assert fm._normalize_domain("youtube.com") == "youtube.com"
    assert fm._normalize_domain("www.youtube.com") == "youtube.com"
    assert fm._normalize_domain("https://youtube.com/") == "youtube.com"
    assert fm._normalize_domain("http://www.youtube.com/watch?v=123") == "youtube.com"
    assert fm._normalize_domain("m.youtube.com") == "m.youtube.com" # Subdomain intact
    assert fm._normalize_domain("HTTPS://WWW.YOUTUBE.COM") == "youtube.com"
    assert fm._normalize_domain("reddit.com:443") == "reddit.com"

def test_domain_matching():
    # Mocking the matching logic from _on_tick
    blocklist = ["youtube.com", "reddit.com"]
    
    def matches(domain):
        for b in blocklist:
            if domain == b or domain.endswith("." + b):
                return True
        return False
        
    assert matches("youtube.com") is True
    assert matches("www.youtube.com") is True
    assert matches("m.youtube.com") is True
    assert matches("reddit.com") is True
    assert matches("old.reddit.com") is True
    
    assert matches("myreddit.com") is False
    assert matches("youtube.com.org") is False
    assert matches("google.com") is False
