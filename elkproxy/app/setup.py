#! /usr/bin/python

from setuptools import setup, find_packages
import os.path

setup(
    name = "elkproxy",
    description = "elkproxy is a filtering proxy for Elastic Search, "
    "and can be used to provide custom per-user query filters for e.g. "
    "Kibana",
    keywords = "elasticsearch kibana",
    install_requires = ["Flask==0.10.1", "requests", "click", "sakstig", "requests"],
    version = "0.0.1",
    author = "RedHog (Egil Moeller)",
    author_email = "egil@innovationgarage.no",
    license = "GPL3",
    url = "https://github.com/innovationgarage/elkproxy",
    packages = find_packages(),
    entry_points={
        'console_scripts': [
            'elkproxy = elkproxy.cli:main',
        ],
        'elkproxy_auths': [
            'return = elkproxy.plugins.common:Return',
            'cookie = elkproxy.plugins.auths:AuthCookie',
            'basic = elkproxy.plugins.auths:AuthBasic'
        ],
        'elkproxy_query_filters': [
            'return = elkproxy.plugins.common:Return',
            'template = elkproxy.plugins.query_filters:QueryFilterTemplate'
        ],
        'elkproxy_doc_savers': [
            'return = elkproxy.plugins.common:Return',
            'template = elkproxy.plugins.doc_savers:DocSaverTemplate'
        ]
    }
)
