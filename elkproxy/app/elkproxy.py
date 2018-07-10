import json
import flask
import requests
import werkzeug.datastructures

app = flask.Flask(__name__)

debug = 0

@app.route('/', methods=['HEAD', 'GET', 'POST'])
@app.route('/<path:path>', methods=['HEAD', 'GET', 'POST'])
def search(path=''):
    if debug > 0: print("%s %s %s" % (flask.request.method, path, flask.request.args))
    if debug > 1: print("    %s" % flask.request.headers)
    if debug > 2: print("    " + "\n    ".join(flask.request.data.decode("utf-8").split('\n')))

    kwargs = {"params": flask.request.args,
              "headers": werkzeug.datastructures.Headers(flask.request.headers)}

    if "Transfer-Encoding" in kwargs["headers"]:
        del kwargs["headers"]["Transfer-Encoding"]
        kwargs["stream"] = True
    
    if flask.request.method == 'HEAD':
        r = requests.head('http://elasticsearch:9200/%s' % path, **kwargs)
    elif flask.request.method == 'POST':
        r = requests.post('http://elasticsearch:9200/%s' % path, data=flask.request.data, **kwargs)
    elif flask.request.method == 'GET':
        r = requests.get('http://elasticsearch:9200/%s' % path, **kwargs)


    if kwargs.get("stream", False):
        content = r.iter_content()
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
    
if __name__ == '__main__':
    app.run(debug=False,host='0.0.0.0', port=9200) #,threaded=True)
        
