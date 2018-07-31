import sakform
import sakstig

class QueryFilterTemplate(object):
    def __init__(self, match=None, filter=None):
        self.match = match
        self.filter = filter
        
    def __call__(self, body, kwargs):
        context = {"body": body,
                   "kwargs": kwargs,
                   "query": [q for q in [body.get("query")] if q is not None]}

        if self.match is not None and not sakstig.QuerySet([context]).execute(self.match):
            return False

        if self.filter is not None:
            body["query"] = {"bool":
                             {"must": context["query"],
                              "filter": sakform.transform(
                                  context,
                                  self.filter)
                             }}
        return body
