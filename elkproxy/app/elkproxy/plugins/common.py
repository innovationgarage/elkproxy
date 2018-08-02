import sakform
import sakstig
import flask

class Return(object):
    def __init__(self, match=None, document=None):
        self.match = match
        self.document = document
        
    def __call__(self, context):
        if self.match is not None and not sakstig.QuerySet([context]).execute(self.match):
            return False
        
        if self.document is not None:
            flask.abort(flask.Response(**sakform.transform(context, self.document)[0]))

        flask.abort(403)
