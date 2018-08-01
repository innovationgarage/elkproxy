import sakform
import sakstig

class DocSaverTemplate(object):
    def __init__(self, match=None, template=None):
        self.match = match
        self.template = template
        
    def __call__(self, body, kwargs):
        context = {"body": body,
                   "kwargs": kwargs}

        if self.match is not None and not sakstig.QuerySet([context]).execute(self.match):
            return False

        if self.template is not None:
            return sakform.transform(context, self.template)[0]

        return body
