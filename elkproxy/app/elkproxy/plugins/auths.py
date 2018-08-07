import sakform
import sakstig
import http.cookies
import hashlib
import logging
import base64

log = logging.getLogger(__name__ + ".details")

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

        log.debug("Authenticated as %s" % value)
        context["kwargs"]["metadata"]["username"] = value
        
        return True

class AuthBasic(object):
    def __init__(self):
        pass
    
    def __call__(self, context):
        if "Authorization" not in context["kwargs"]["headers"]:
            return False
        auth = context["kwargs"]["headers"]["Authorization"]
        if not auth.startswith("Basic"):
            return False
        auth = base64.b64decode(auth.split(" ")[-1]).decode("utf-8")
        username, password = auth.split(":")

        log.debug("Authenticated as %s" % username) 
        context["kwargs"]["metadata"]["username"] = username
        context["kwargs"]["metadata"]["password"] = password
       
        return True
