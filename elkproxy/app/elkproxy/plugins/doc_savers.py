import sakform
import sakstig
import flask

class DocSaverTemplate(object):
    def __init__(self, match=None, template=None):
        self.match = match
        self.template = template
        
    def __call__(self, context):
        if self.match is not None and not sakstig.QuerySet([context]).execute(self.match):
            return False

        if self.template is not None:
            return sakform.transform(context, self.template)[0]
        
        return context["body"]
