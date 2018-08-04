
# &nbsp;<img src="ElkProxy.svg" alt="logo" height="40px"> elkproxy

ElkProxy is a highly configurable proxy server that sits in front of an Elastic Search server and filters/rewrites searches,
document downloads, uploads, and updates.

The proxy uses a plugin system and a json based configuration file that scripts the plugins.

# Installing elkproxy

    cd elkproxy/app
    python3 setup.py install

# Running elkproxy

    elkproxy --config myconfig.json

# Demo environment

This repository comes with a docker compose demo environment based on
the official open source version of the ELK (Elastic Search, Logstash,
Kibana) stack. It can be started with the following command

    docker compose up -d

and will expose kibana with some testing data on http://localhost:5601. You can modify elkproxy/app/config.json and run

    docker-compose stop elkproxy
    docker-compose up elkproxy

to try out different configurations. If you run the elkproxy container
without -d, logging configured in config.json will print to your
terminal, making it possible to debug your plugin scripts.


# Config language

At the top level, the configuration consist of a JSON object with a set of properties described below

## Upstream ElastSearch url

    "upstream": "http://elasticsearch:9200"

The url to the upstream ElastSearch that elkproxy should connect to.

## Server hostname and port

    "host": "localhost:9200"

The hostname (interface) and port that elkproxy should be reachable at.

## Logging

    "logging": {
        "version": 1,
        "loggers": {...},
        "handlers": {...},
        "formatters": {...}}

Python logging configuration, in the format that can be supplied to
[logging.config.dictConfig](https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig).

## Plugin points and script lists

    "auths": [{"type": "cookie",
               "args": {...}}
              ...],
    "query_filters": [{"type": "template",
                       "args": {...}},
                      {"type": "rest",
                       "args": {...}}
                      ...],
    "doc_savers": [{"type": "template",
                    "args": {...}},
                   {"type": "template",
                    "args": {...}}
                   ...]
                     
The main operation of elkproxy is controlled by script lists run at
various plugin points. The plugin points are for authentication
plugins, filters for elastic search queries and filters for uploaded
documents, respectively.

A script list is executed in order from top to bottom until a line is reached that is able to process the request.
That is, if multiple lines match a given request, the first one will be executed.

Each script list line consists of a type and some arguments. The type is the name of a plugin class (a python entrypoint
registered by an installed python package), and the arguments are (named) constructor arguments to the python class. It is entirely
up to the class to determine what arguments are accepted or required, or what they mean.

## Sakstig expressions and sakform templates

Some of the plugins can be scripted using
[sakstig](https://innovationgarage.github.io/sakstig/) expressions for
matching requests, and using
[sakform](https://innovationgarage.github.io/sakstig/) templates for
generating queries and documents. These allow fine grained
programmatic control of JSON data matching and transformation,
respectively.

### Sakstig extensions

#### http()
The SakStig function

    http(url, {name=value...})

makes a http request using the python requests module. The optional
dictionary of named parameters is sent to the requests method except
for the parameter `method` that is used to select the method itself
(it defaults to `get`). The function returns a QuerySet with one
dictionary in it with the following members:

    {"status": HTTP_STATUS,
     "content": STRING_OR_JSON_OBJECT,
     "headers": {NAME:VALUE...}}


### Execution context

Plugins run in a plugin point dependent context, described under each
plugin point below. However, all contexts share a `kwargs` member with
a dictionary of the http request properties. Plugins are free to
modify these properties _even_if_ they do not match the current
request, and script execution continues with the next line.

    KWARGS = {"metadata": METADATA_DICT,
              "method": HTTP_METHOD,
              "params": URL_ARGS,
              "headers": HTTP_HEADERS,
              "path": URL_PATH}}

METADATA is a dictionary that starts out empty, but that can be
populated and modified by plugins. It is not used when generating the
http request to the upstream ElasticSearch server. Instead, it can be
used to transfer data between blugins, e.g. for storing user
authentication data by the auth plugins that is later accessed by e.g.
query filter plugins to generate restricted queries for the current
user.

## Available plugins

### Plugins common to all plugin points

#### Return

    {"type": "return",
     "args": {"match": "$[@.kwargs.path is '_template/kibana_index_template:.kibana']",
              "document": {"response": {}, "status":200}}}

The return plugin matches the current request using a sakstig
expression, and uses a sakform template to generate a direct response,
without passing the request on to the real ElasticSearch server.

Since the sakstig expression can do http queries, it is possible to
use this to e.g. check if a document already exists, or has a certain
property set to some value, before allowing a document upload to
proceed.


### Auth plugins
Authentication plugins sets $.kwargs.metadata.username to the name of the authenticated user if they succeed.

#### Cookie

    {"type": "cookie",
     "args": {"name": "COOKIE NAME", "secret": "MY SECRET", "hashfunction": "md5"}}

The cookie plugin authenticates against a simple hash signed cookie. The cookie value must be on the format

    username:hash

where `hash` must match `hashfunction(username+secret)`. The supported hashfunctions are the ones available in
the python `hashlib` module.

### Query filter plugins

Query filter plugins provide extra `filter` context query terms that
are logically ANDed to elastic search queries. They are run in the
following context:

    {"query": ES_QUERY,
     "body": REQUEST_BODY,
     "kwargs": KWARGS}


#### Template
    {"type": "template",
     "args": {"match": "$[@.query.*.bool.filter.*.term.type is 'index-pattern']",
              "filter": {"term": {"config.username" : {"$": "$.kwargs.metadata.username"}}}}}

The template plugin matches the query using a sakstig expression, and
uses a sakform template to generate the extra query terms to be ANDed
with the user query.

Both match and filter are optional - if match is missing, the line
matches any query, if filter is missing, no extra terms are added to
the query.

### Document saver plugins

Document saver plugins can rewrite documents uploaded to
ElasticSearch. They are run in the following context:

    {"body": DOCUMENT_BODY,
     "kwargs": KWARGS}

#### Template
    {"type": "template",
     "args": {"match": "$[@.body.type is 'mydoc']",
              "template": {
                  "username": {"$": "$.kwargs.metadata.username"},
                  "_": {"$": "$.body + @template()"}}}}

The template plugin matches the document body using a sakstig expression, and
uses a sakform template to rewrite it.

Both match and template are optional - if match is missing, the line
matches andy document, if template is missing the document is left
unchanged.

# Example config
Example [config.json](https://github.com/innovationgarage/elkproxy/blob/master/elkproxy/app/config.json) suitable for kibana.

# How to write plugins
Plugins are python classes that are registered using setuptools entrypoints. The entry points are named after the plugin points, prefixed by "elkproxy_". Here, an auths plugin "myplugin" is registered:

    setup(
        entry_points={
            'elkproxy_auths': [
                'myplugin = mypackage.mymodule:MyPluginClass'
            ]})

Plugin classes are instantiated with keyword constructor arguments taken from the script line. It is entirely up to the
plugin what arguments to accept or require, and how to interpret them.

Plugin instances must be callable, and are always called with a dictionary containing at least two members: `body` and `kwargs`. `kwargs` is the request kwargs, as described above, while `body` depends on the plugin point - for `query_filters`, this would be the query, for `doc_savers` its the document, and for `auths` it's just `None`.

Plugins are expected to return either `False`, meaning that the script list execution continues, or some other value, meaning that the script list execution finishes with that value as output. For `query_filters` this is a query term to logically AND with the original query, for `doc_savers` this is the rewritten document body. For `auths` the output value is ignored.

Note that plugins can modify the value of `kwargs`, even if they return `False`.

    class MyPluginClass(object):
        def __init__(self, **args):
            pass
        def __call__(self, context):
            return True
