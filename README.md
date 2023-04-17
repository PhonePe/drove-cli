# Drove CLI

Command line interface for the Drove Container Orchestrator.

## Installation
To install the required dependencies please run the following command:

```
pip install -r requirements.txt
```

# Getting Started

## Accessing the Documentation
The arguments needed by the script are self documenting. Please use `-h` or `--help` in different sections and sub-sections of the CLI to get descriptions of commands, sub-commands, their arguments and options.

To see basic help:
```

$ ./drove -h

usage: drove [-h] [--endpoint ENDPOINT] [--auth-header AUTH_HEADER] [--insecure INSECURE] [--config CONFIG] {cluster,tasks,appinstances,executor,apps} ...

positional arguments:
  {cluster,tasks,appinstances,executor,apps}
                        Available plugins
    cluster             Drove cluster related commands
    tasks               Drove task related commands
    appinstances        Drove application instance related commands
    executor            Drove cluster executor related commands
    apps                Drove application related commands

optional arguments:
  -h, --help            show this help message and exit
  --endpoint ENDPOINT, -e ENDPOINT
                        Drove endpoint. (For example: https://drove.test.com)
  --auth-header AUTH_HEADER, -t AUTH_HEADER
                        Authorization header value for the provided drove endpoint
  --insecure INSECURE, -i INSECURE
                        Do not verify SSL cert for server
  --config CONFIG, -c CONFIG
                        Configuration file for drove client

```

To see documentation for a command/section:
```
$ ./drove cluster -h
usage: drove cluster [-h] {ping,summary,leader,endpoints,events} ...

positional arguments:
  {ping,summary,leader,endpoints,events}
                        Available commands for cluster management
    ping                Ping the cluster
    summary             Show cluster summary
    leader              Show leader for cluster
    endpoints           Show all exposed endpoints
    events              Events on the cluster

optional arguments:
  -h, --help            show this help message and exit
```

To further drill down into options for a sub-command/subsection:
```
$ ./drove cluster events -h
usage: drove cluster events [-h] [--follow] [--type TYPE] [--count COUNT] [--textfmt TEXTFMT]

optional arguments:
  -h, --help            show this help message and exit
  --follow, -f          Follow events (Press CTRL-C to kill)
  --type TYPE, -t TYPE  Output events of only the matching type
  --count COUNT, -c COUNT
                        Fetch <count> events at a time.
  --textfmt TEXTFMT, -s TEXTFMT
                        Use the format string to print message
```

# Connecting to the Drove cluster

In order to use the CLI, we need to provide coordinates to the cluster to connect to. This can be done in the following manner:

## Drove CLI config file
The config file can be located in the following paths:
* `.drove` file in your home directory (Typically used for the default cluster you frequently connect to)
*  A file in any path that can be passed as a parameter to the CLI with the `-c CONFIG` option

File format:
```
endpoint = https://yourcluster.yourdomain.com
insecure = true
username = <your_username>
password = <your_password>
auth_header= <Authorization value here if using header based auth>
```

Authentication priority:
* If both `username` and `password` are provided, basic auth is used.
* If a value is provided in the `auth_header` parameter, it is passed as the value for the `Authorization` header in the upstream HTTP calls to the Drove server verbatim.
* If neither, no auth is set

> NOTE: Use the `insecure` option to skip certificate checks on the server endpoint (comes in handy for internal domains)

To use a cusom config file, invoke drove in the following form:

```
$ ./drove -c custom.conf ...
```

## Command line options
Pass the endpoint and other options using `--endpoint|-e` etc etc. Options can be obtained using `-h` as mentioned above. Invocation will be in the form:

```
$ ./drove -e http://localhost:10000 -u guest -p guest ...
```

## Command sections
Drove CLI commands are organised in the following sections
* **_cluster_** - Drove cluster related commands
* **_executor_** - Drove cluster executor related commands
* **_apps_** - Application related commands
* **_appinstances_** - Drove application instance related commands
* **_tasks_** - Drove task related commands

Please use `./drove <command> -h` to see the list of operations provided for each command section.