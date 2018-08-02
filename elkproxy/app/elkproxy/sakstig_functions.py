import sakstig
import requests

class http(sakstig.Function):
    def call(self, global_qs, local_qs, args):
        args = sakstig.QuerySet(args).flatten()
        
        kwargs = {}
        if sakstig.is_dict(args[-1]):
            kwargs = args[-1]
            args = args[:-1]

        method = kwargs.pop("method", "get")

        r = getattr(requests, method)(*args, **kwargs)

        try:
            content = r.json()
        except:
            content = r.content
        
        return sakstig.QuerySet([{
            "status": r.status_code,
            "content": content,
            "headers": r.headers
        }])

