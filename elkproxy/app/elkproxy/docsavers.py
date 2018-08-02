import sakform
import sakstig
import flask

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

class DocSaverReturn(object):
    def __init__(self, match=None, document=None):
        self.match = match
        self.document = document
        
    def __call__(self, body, kwargs):
        context = {"body": body,
                   "kwargs": kwargs}

        if self.match is not None and not sakstig.QuerySet([context]).execute(self.match):
            return False
        
        if self.document is not None:
            flask.abort(flask.Response(**sakform.transform(context, self.document)[0]))

        flask.abort(403)
