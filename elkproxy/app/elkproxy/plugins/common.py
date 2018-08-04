import sakform
import sakstig
import flask
import json

class Return(object):
    def __init__(self, match=None, document=None):
        self.match = match
        self.document = document
        
    def __call__(self, context):
        if self.match is not None and not sakstig.QuerySet([context]).execute(self.match):
            return False
        
        if self.document is not None:
            res = sakform.transform(context, self.document)[0]
            if "response" in res and not isinstance(res["response"], (str, bytes)):
                res["response"] = json.dumps(res["response"])
            flask.abort(flask.Response(**res))

        flask.abort(403)
