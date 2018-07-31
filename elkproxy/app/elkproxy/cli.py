import click
import json
import elkproxy.proxy
import os.path

@click.command()
@click.option('-d', '--debug', type=int)
@click.option('-h', '--host')
@click.option('-c', '--config', default='~/.config/elkproxy.json')
def main(config, **kwargs):
    with open(os.path.expanduser(config)) as f:
        config = json.load(f)
    config.update({name: value for (name, value) in kwargs.items() if value is not None})
    
    elkproxy.proxy.Proxy(config).run()
