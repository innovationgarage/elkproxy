import sakform
import sakstig

class QueryFilterTemplate(object):
    def __init__(self, match=None, filter=None):
        self.match = match
        self.filter = filter
        
    def __call__(self, context):
        if self.match is not None and not sakstig.QuerySet([context]).execute(self.match):
            return False

        if self.filter is not None:
            context['body']["query"] = {"bool":
                                        {"must": context["query"],
                                         "filter": sakform.transform(
                                             context,
                                             self.filter)
                                        }}
        return context['body']
