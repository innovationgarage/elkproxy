import sakform
import sakstig
import http.cookies
import hashlib

class AuthCookie(object):
    def __init__(self, name, secret=None, hashfunction=None):
        self.name = name
        self.secret = secret
        self.hashfunction = hashfunction
        
    def __call__(self, context):
        cookies = http.cookies.SimpleCookie(context["kwargs"]["headers"].get("Cookie"))
        if self.name not in cookies:
            return False
        value = cookies[self.name].value

        if self.secret is not None or self.hashfunction is not None:
            value, hsh = value.split(":")
            if getattr(hashlib, self.hashfunction or 'md5')(value + secret).hexdigest() != hsh:
                return False

        print("Authenticated as %s" % value)
        context["kwargs"]["metadata"]["username"] = value
        
        return True
