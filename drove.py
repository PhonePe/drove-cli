#!/usr/bin/python3 -u

import argparse
import drovecli
import droveclient
import droveutils
import traceback

def build_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(prog="drove")

    parser.add_argument("--file", "-f", help="Configuration file for drove client")
    parser.add_argument("--cluster", "-c", help="Cluster name as specified in config file")
    parser.add_argument("--endpoint", "-e", help="Drove endpoint. (For example: https://drove.test.com)")
    parser.add_argument("--auth-header", "-t", dest="auth_header", help="Authorization header value for the provided drove endpoint")
    parser.add_argument("--insecure", "-i", help="Do not verify SSL cert for server")
    parser.add_argument("--username", "-u", help="Drove cluster username")
    parser.add_argument("--password", "-p", help="Drove cluster password")
    parser.add_argument("--debug", "-d", help="Print details of errors", default=False, action="store_true")
    return parser

def get_parser():
    parser = build_parser()
    client = None
    client = drovecli.DroveCli(parser)
    return client.parser
 

def run():
    parser = build_parser()
    client = None
    try:
        client = drovecli.DroveCli(parser)
        client.run()
    except (BrokenPipeError, IOError, KeyboardInterrupt):
        pass
    except droveclient.DroveException as e:
        debug = True if client != None and client.debug else False
        droveutils.print_drove_error(e, debug)
        if debug:
            traceback.print_exc()

    except Exception as e:
        print("Drove CLI error: " + str(e))
        debug = True if client != None and client.debug else False
        if debug:
            traceback.print_exc()
        else:
            parser.print_help()

if __name__ == '__main__':
    run()
