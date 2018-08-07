import json
import flask
import requests
import werkzeug.datastructures
import werkzeug.exceptions
import logging
import pkg_resources
import elkproxy.sakstig_functions
import logging
import logging.config
import traceback

log = logging.getLogger(__name__)
log_request = logging.getLogger(__name__ + ".request")

log_auths = logging.getLogger("elkproxy.plugins.auths.run")
log_query_filters = logging.getLogger("elkproxy.plugins.query_filters.run")
log_doc_savers = logging.getLogger("elkproxy.plugins.doc_savers.run")

def flatten(it):
    return (item for sublist in it for item in sublist)

plugin_categories = ("auths", "query_filters", "doc_savers")

plugins = {}
for plugin_category in plugin_categories:
    plugins[plugin_category] = {}
    for entry_point in pkg_resources.iter_entry_points("elkproxy_" + plugin_category):
        plugins[plugin_category][entry_point.name] = entry_point.load()

class Proxy(object):
    def __init__(self, config):
        logging.config.dictConfig(config.get('logging', {"version": 1}))
        
        log.info("Available plugins:")
        for category, catplugins in plugins.items():
            log.info("  %s: %s"  % (category, ", ".join(catplugins.keys())))
        log.info("")

        self.plugins = {}
        for plugin_category in plugin_categories:
            self.plugins[plugin_category] = []
            for plugin_spec in config.get(plugin_category, []):
                plugin = plugins[plugin_category][plugin_spec["type"]](**plugin_spec.get("args", {}))
                plugin.spec = plugin_spec
                self.plugins[plugin_category].append(plugin)

        self.url = config.get("upstream", "http://elasticsearch:9200")
            
        host, port = config.get("host", ":").split(":")
        host = host or '0.0.0.0'
        port = port and int(port) or 9200
        self.host = host
        self.port = port

        self.app = flask.Flask(__name__)
        
        @self.app.route('/', methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])
        @self.app.route('/<path:path>', methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])
        def process(path=''):
            try:
                return self.process(path)
            except werkzeug.exceptions.HTTPException as e:
                raise
            except Exception as e:
                import traceback
                print(e)
                traceback.print_exc()
                raise

    def run(self, *arg, **kw):
        self.app.run(debug=False,
                     host=self.host,
                     port=self.port, *arg, **kw) #,threaded=True)
        
    def process_plugins(self, category, context, default=None, log=log):
        log.info("%s processing %s" % (category, context))
        for plugin in self.plugins[category]:
            descr = "%s.%s(%s)" % (category, plugin.spec["type"], plugin.spec.get("args", ""))
            try:
                res = plugin(context)
                if res:
                    log.info("  %s matched ->" % (descr,))
                    log.info("    %s" % (res,))
                    log.info("\n\n")
                    return res
                else:
                    log.warn("  %s NOT matched" % (descr,))
            except werkzeug.exceptions.HTTPException as e:
                raise
            except Exception as e:
                log.error("  %s failed with %s:\n%s" % (descr, e, traceback.format_exc()))
        log.info("\n\n")
        return default
        
    def search_query_filter(self, body, kwargs):
        context = {"body": body,
                   "kwargs": kwargs,
                   "query": [q for q in [body.get("query")] if q is not None]}
        return self.process_plugins("query_filters", context, default=body, log=log_query_filters)

    def doc_filter(self, body, kwargs):
        context = {"body": body,
                   "kwargs": kwargs}        
        return self.process_plugins("doc_savers", context, default=body, log=log_doc_savers)

    def request_filter(self, kwargs):
        self.process_plugins("auths", {"kwargs": kwargs}, log=log_auths)
        
        if "_msearch" in kwargs["path"]:
            lines = [json.loads(line) for line in kwargs["data"].strip(b"\n").split(b"\n")]
            kwargs["data"] = '\n'.join(json.dumps(line)
                                       for line in flatten((header, self.search_query_filter(body, kwargs))
                                                           for header, body in zip(*[iter(lines)]*2))) + '\n'
        elif "_search" in kwargs["path"]:
           kwargs["data"] = json.dumps(self.search_query_filter(json.loads(kwargs["data"]), kwargs))
        elif kwargs["method"] == "PUT" and not kwargs["path"].split("/")[-1].startswith("_"):
            # Add document
            kwargs["data"] = json.dumps(self.doc_filter(json.loads(kwargs["data"]), kwargs))
        elif kwargs["method"] == "POST" and not kwargs["path"].split("/")[-1].startswith("_"):
            # Add document with automatic ID
            kwargs["data"] = json.dumps(self.doc_filter(json.loads(kwargs["data"]), kwargs))
        # elif flask.request.method in ("POST", "PUT"):
        #     print("================{")
        #     print(flask.request.method)
        #     print(kwargs)
        #     print("================{")
        #     print("}================\n\n")
        return kwargs

    def process(self, path=''):
        log_request.info("%s %s %s" % (flask.request.method, path, flask.request.args))
        log_request.debug("    %s" % flask.request.headers)
        log_request.debug("    " + "\n    ".join(flask.request.data.decode("utf-8").split('\n')))

        kwargs = {"metadata": {},
                  "method": flask.request.method,
                  "params": flask.request.args,
                  "headers": werkzeug.datastructures.Headers(flask.request.headers),
                  "data": flask.request.data,
                  "path": path}

        if "Transfer-Encoding" in kwargs["headers"]:
            del kwargs["headers"]["Transfer-Encoding"]
            kwargs["stream"] = True
        if 'search' in path:
            kwargs["stream"] = True

        kwargs = self.request_filter(kwargs)

        url = '%s/%s' % (self.url, kwargs.pop("path"))

        method = kwargs.pop("method")
        kwargs.pop("metadata", None)

        if method == 'HEAD':   r = requests.head(url, **kwargs)
        elif method == 'POST': r = requests.post(url, **kwargs)
        elif method == 'GET':  r = requests.get(url, **kwargs)
        elif method == 'PUT':  r = requests.put(url, **kwargs)
        elif method == 'DELETE':  r = requests.delete(url, **kwargs)

        if kwargs.get("stream", False):
            content = r.iter_content(chunk_size=4096)
        else:
            content = r.text

        if r.status_code == 200:
            low = log_request.info
            high = log_request.debug
        else:
            low = log_request.warn
            high = log_request.info            
            
        low("    -> %s" % r.status_code)
        high("    %s" % r.headers)
        if kwargs.get("stream", False):
            high("        STREAM")
        else:
            high("        " + "\n        ".join(content.split('\n')))

        resp = flask.Response(content, r.status_code)
        for key, value in r.headers.items():
            if key == 'content-encoding': continue # requests decodes this for us, so keeping this is misleading our client, breaking stuff
            resp.headers[key] = value
        return resp
