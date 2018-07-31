import json
import flask
import requests
import werkzeug.datastructures
import logging
import pkg_resources

def flatten(it):
    return (item for sublist in it for item in sublist)

plugin_categories = ("auths", "query_filters", "doc_savers")

plugins = {}
for plugin_category in plugin_categories:
    plugins[plugin_category] = {}
    for entry_point in pkg_resources.iter_entry_points("elkproxy_" + plugin_category):
        plugins[plugin_category][entry_point.name] = entry_point.load()

print("Available plugins:")
for category, catplugins in plugins.items():
    print("  %s: %s"  % (category, ", ".join(catplugins.keys())))
print()

class Proxy(object):
    def __init__(self, config):
        self.plugins = {}
        for plugin_category in plugin_categories:
            self.plugins[plugin_category] = []
            for plugin_spec in config.get(plugin_category, []):
                plugin = plugins[plugin_category][plugin_spec["type"]](**plugin_spec.get("args", {}))
                plugin.spec = plugin_spec
                self.plugins[plugin_category].append(plugin)

        self.debug = config.get("debug", 0)
        if self.debug == 0:
            logging.getLogger('werkzeug').setLevel(logging.ERROR)
        
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
            except Exception as e:
                import traceback
                print(e)
                traceback.print_exc()
                raise

    def run(self, *arg, **kw):
        self.app.run(debug=False,
                     host=self.host,
                     port=self.port, *arg, **kw) #,threaded=True)
        
    def process_plugins(self, category, data, kwargs):
        print("%s processing %s (%s)" % (category, data, kwargs))
        for plugin in self.plugins[category]:
            descr = "%s.%s(%s)" % (category, plugin.spec["type"], plugin.spec.get("args", ""))
            try:
                res = plugin(data, kwargs)
                if res:
                    print("  %s matched ->" % (descr,))
                    print("    %s" % (res,))
                    print("\n\n")
                    return res
                else:
                    print("  %s NOT matched" % (descr,))
            except Exception as e:
                print("  %s failed with %s" % (descr, e))
                import traceback
                traceback.print_exc()
        print("\n\n")
        return data
        
    def search_query_filter(self, body, kwargs):
        return self.process_plugins("query_filters", body, kwargs)

    def doc_filter(self, body, kwargs):
        return self.process_plugins("doc_savers", body, kwargs)

    def request_filter(self, kwargs):
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
        if self.debug > 0: print("%s %s %s" % (flask.request.method, path, flask.request.args))
        if self.debug > 1: print("    %s" % flask.request.headers)
        if self.debug > 2: print("    " + "\n    ".join(flask.request.data.decode("utf-8").split('\n')))

        kwargs = {"method": flask.request.method,
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

        url = 'http://elasticsearch:9200/%s' % kwargs.pop("path")

        method = kwargs.pop("method")

        if method == 'HEAD':   r = requests.head(url, **kwargs)
        elif method == 'POST': r = requests.post(url, **kwargs)
        elif method == 'GET':  r = requests.get(url, **kwargs)
        elif method == 'PUT':  r = requests.put(url, **kwargs)
        elif method == 'DELETE':  r = requests.delete(url, **kwargs)

        if kwargs.get("stream", False):
            content = r.iter_content(chunk_size=4096)
        else:
            content = r.text

        if self.debug > 0: print("    ->", r.status_code)
        if self.debug > 1: print("    %s" % r.headers)
        if self.debug > 2:
            if kwargs.get("stream", False):
                print("        STREAM")
            else:
                print("        " + "\n        ".join(content.split('\n')))

        resp = flask.Response(content, r.status_code)
        for key, value in r.headers.items():
            if key == 'content-encoding': continue # requests decodes this for us, so keeping this is misleading our client, breaking stuff
            resp.headers[key] = value
        return resp
