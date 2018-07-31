import json
import flask
import requests
import werkzeug.datastructures
import logging

app = flask.Flask(__name__)

debug = 0

if debug == 0:
    logging.getLogger('werkzeug').setLevel(logging.ERROR)

def flatten(it):
    return (item for sublist in it for item in sublist)
    
def search_query_filter(body, kwargs):
    if body.get("query") == {"bool":{"filter":[{"term":{"type":"index-pattern"}}]}}:
        return body

    if body.get("aggs") == {"indices":{"terms":{"field":"_index","size":120}}}:
        return body

    body["query"] = {"bool":
                     {"must": [q for q in [body.get("query")] if q is not None],
                      "filter": [{
                         "query_string": {
                             "query": "/styles/ad-blocker.css",
                             "analyze_wildcard": True,
                             "default_field": "*"
                         }}]
                     }}
    return body

def request_filter(kwargs):
    if "_msearch" in kwargs["path"]:
        print("ORIGINAL: %s" % kwargs["data"])
        lines = [json.loads(line) for line in kwargs["data"].strip(b"\n").split(b"\n")]
        kwargs["data"] = '\n'.join(json.dumps(line)
                                   for line in flatten((header, search_query_filter(body, kwargs))
                                                       for header, body in zip(*[iter(lines)]*2))) + '\n'
        print("FILTERED: %s" % kwargs["data"])
    elif "_search" in kwargs["path"]:
        print(flask.request.headers)
        print("\n")
        print("ORIGINAL: %s" % kwargs["data"])
        kwargs["data"] = json.dumps(search_query_filter(json.loads(kwargs["data"]), kwargs))
        print("FILTERED: %s" % kwargs["data"])
        print("\n\n")
    return kwargs

@app.route('/', methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:path>', methods=['HEAD', 'GET', 'POST', 'PUT', 'DELETE'])
def search(path=''):
    try:
        if debug > 0: print("%s %s %s" % (flask.request.method, path, flask.request.args))
        if debug > 1: print("    %s" % flask.request.headers)
        if debug > 2: print("    " + "\n    ".join(flask.request.data.decode("utf-8").split('\n')))

        kwargs = {"params": flask.request.args,
                  "headers": werkzeug.datastructures.Headers(flask.request.headers),
                  "data": flask.request.data,
                  "path": path}
                
        if "Transfer-Encoding" in kwargs["headers"]:
            del kwargs["headers"]["Transfer-Encoding"]
            kwargs["stream"] = True
        if 'search' in path:
            kwargs["stream"] = True

        kwargs = request_filter(kwargs)
            
        url = 'http://elasticsearch:9200/%s' % kwargs.pop("path")

        if flask.request.method == 'HEAD':   r = requests.head(url, **kwargs)
        elif flask.request.method == 'POST': r = requests.post(url, **kwargs)
        elif flask.request.method == 'GET':  r = requests.get(url, **kwargs)
        elif flask.request.method == 'PUT':  r = requests.put(url, **kwargs)
        elif flask.request.method == 'DELETE':  r = requests.delete(url, **kwargs)
        
        if kwargs.get("stream", False):
            content = r.iter_content(chunk_size=4096)
        else:
            content = r.text
            
        if debug > 0: print("    ->", r.status_code)
        if debug > 1: print("    %s" % r.headers)
        if debug > 2:
            if kwargs.get("stream", False):
                print("        STREAM")
            else:
                print("        " + "\n        ".join(content.split('\n')))

        resp = flask.Response(content, r.status_code)
        for key, value in r.headers.items():
            if key == 'content-encoding': continue # requests decodes this for us, so keeping this is misleading our client, breaking stuff
            resp.headers[key] = value
        return resp
    except Exception as e:
        import traceback
        print(e)
        traceback.print_exc()
        raise
    
if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0', port=9200) #,threaded=True)
        
