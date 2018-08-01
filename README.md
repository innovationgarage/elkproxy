
# &nbsp;<img src="ElkProxy.svg" alt="logo" height="40px"> elkproxy

ElkProxy is a highly configurable proxy server that sits in front of an Elastic Search server and filters/rewrites searches,
document downloads, uploads, and updates.

The proxy uses a plugin system and a json based configuration file that scripts the plugins.

# Installing elkproxy

    cd elkproxy/app
    python3 setup.py install

# Running elkproxy

    elkproxy --config myconfig.json
    
# Config language

At the top level, the configuration consists of a set of plugin points with a script list for each. Example:

    {"auths": [{"type": "cookie",
                "args": {...}}],
     "query_filters": [{"type": "template",
                        "args": {...}},
                       {"type": "rest",
                        "args": {...}}],
     "doc_savers": [{"type": "template",
                     "args": {...}},
                    {"type": "template",
                     "args": {...}}]}
                     
The plugin points are for authentication plugins, filters for elastic search queries and
filters for uploaded documents, respectively.

A script list is executed in order from top to bottom until a line is reached that is able to process the request.
That is, if multiple lines match a given request, the first one will be executed.

Each script list line consists of a type and some arguments. The type is the name of a plugin class (a python entrypoint
registered by an installed python package), and the arguments are (named) constructor arguments to the python class. It is entirely
up to the class to determine what arguments are accepted or required, or what they mean.

# Available plugins
## Auth plugins
Authentication plugins sets $.kwargs.metadata.username to the name of the authenticated user if they succeed.

### Cookie

    {"type": "cookie",
     "args": {"name": "COOKIE NAME", "secret": "MY SECRET", "hashfunction": "md5"}}

The cookie plugin authenticates against a simple hash signed cookie. The cookie value must be on the format

    username:hash

where `hash` must match `hashfunction(username+secret)`. The supported hashfunctions are the ones available in
the python `hashlib` module.

## Query filter plugins

Query filter plugins provide extra `filter` context query terms that are logically ANDed to elastic search queries.

### Template

    {"type": "template",
     "args": {"match": "$[@.query.*.bool.filter.*.term.type is 'index-pattern']",
              "filter": {"term": {"config.username" : {"$": "$.kwargs.metadata.username"}}}}}

The template plugin matches the query using a [sakstig](https://innovationgarage.github.io/sakstig/) expression, and
uses a [sakform](https://innovationgarage.github.io/sakstig/) template to generate the extra query terms to be ANDed
with the user query. The `$` context that the `match` expression and the `filter` template run against consists of

    {"query": ES_QUERY,
     "body": REQUEST_BODY,
     "kwargs": KWARGS}

Both match and filter are optional - if match is missing, the line matches andy query, if filter is missing, no extra terms
are added to the query.

## Document saver plugins
### Template
    {"type": "template",
     "args": {"match": "$[@.body.type is 'mydoc']",
              "template": {
                  "username": {"$": "$.kwargs.metadata.username"},
                  "_": {"$": "$.body + @template()"}}}}

The template plugin matches the document body using a [sakstig](https://innovationgarage.github.io/sakstig/) expression, and
uses a [sakform](https://innovationgarage.github.io/sakstig/) template to rewrite it.  The `$` context that the `match` expression and the `template` template run against consists of

    {"body": DOCUMENT_BODY,
     "kwargs": KWARGS}

Both match and template are optional - if match is missing, the line matches andy document, if template is missing the document is left unchanged.


# Request kwargs

Plugins generally have access to, and can modify, a dictionary of request data. The dictionary has the following members

    "kwargs": {"metadata": METADATA_DICT,
               "method": HTTP_METHOD,
               "params": URL_ARGS,
               "headers": HTTP_HEADERS,
               "path": URL_PATH}}

METADATA is in turn a dictionary that starts out empty, but that can be modified by plugins. This is used e.g.
for storing user authentication data by the auth plugins.

# Example config
Example [config.json](https://github.com/innovationgarage/elkproxy/blob/master/elkproxy/app/config.json) suitable for kibana.
