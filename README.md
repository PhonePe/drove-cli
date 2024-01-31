# Drove CLI

Command line interface for the Drove Container Orchestrator.

# Getting Started

## Installation

### Create Virtual Environment

```bash
VENV_BASE_DIRECTORY=/path/to/base/directory/for/virtual/env
cd ${VENV_BASE_DIRECTORY}
python3 -m venv drove_cli
```

### Activate Virtual Environment

```bash
cd ${VENV_BASE_DIRECTORY}/drove_cli
source bin/activate
```

### Install or Upgrade drove_cli using Pip

```bash
# For installing/upgrading to latest snapshot version
pip3 install --index https://artifactory.phonepe.com/repository/pypi-snapshots/simple --extra-index-url https://artifactory.phonepe.com/repository/pypi-org/simple --ignore-installed --force-reinstall --no-cache-dir com.phonepe.infra.drove_cli

# For installing/upgrading to latest release version
pip3 install --index https://artifactory.phonepe.com/repository/pypi-releases/simple --extra-index-url https://artifactory.phonepe.com/repository/pypi-org/simple com.phonepe.infra.drove_cli
```

After installation `drove` command can be used as per user guide provided below. Once usage of `drove` is done, virtual environment can be deactivated.

### Deactivate Virtual Environment

```bash
deactivate
```

Reactivate/deactivate virtual environment based on the need to utilize drove cli.

## Requirements
The CLI is written in Python 3x


## Accessing the Documentation
The arguments needed by the script are self documenting. Please use `-h` or `--help` in different sections and sub-sections of the CLI to get descriptions of commands, sub-commands, their arguments and options.

To see basic help:
```

$ drove -h

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
$ drove cluster -h
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
$ drove cluster events -h
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
$ drove -c custom.conf ...
```

## Command line options
Pass the endpoint and other options using `--endpoint|-e` etc etc. Options can be obtained using `-h` as mentioned above. Invocation will be in the form:

```
$ drove -e http://localhost:10000 -u guest -p guest ...
```

## CLI format
The following cli format is followed:

```
drove [-h] [--config CONFIG] [--endpoint ENDPOINT] [--auth-header AUTH_HEADER] [--insecure INSECURE] [--username USERNAME] [--password PASSWORD] [--debug] {executor,cluster,apps,appinstances,tasks} ...
```

### Basic Arguments

        --config CONFIG, -c CONFIG
                        Configuration file for drove client
        --endpoint ENDPOINT, -e ENDPOINT
                        Drove endpoint. (For example: https:drove.test.com) (Config option: endpoint)
        --auth-header AUTH_HEADER, -t AUTH_HEADER
                        Authorization header value for the provided drove endpoint (Config option: auth_header)
        --insecure INSECURE, -i INSECURE
                        Do not verify SSL cert for server (Config option: insecure)
        --username USERNAME, -u USERNAME
                        Drove cluster username (Config option: username)
        --password PASSWORD, -p PASSWORD
                        Drove cluster password  (Config option: password)
        --debug, -d           Print details of errors

## Commands
Commands in drove are meant to address specific functionality. They can be summarized as follows:
```
    executor            Drove cluster executor related commands
    cluster             Drove cluster related commands
    apps                Drove application related commands
    appinstances        Drove application instance related commands
    tasks               Drove task related commands
```
### executor
---
Drove cluster executor related commands

```
drove executor [-h] {list,info,appinstances,tasks} ...
```

#### Sub-commands

##### list

List all executors

```
drove executor list [-h]
```

##### info

Show details about executor

```
drove executor info [-h] executor-id
```

###### Positional Arguments

`executor-id` - Executor id for which info is to be shown

##### appinstances

Show app instances running on this executor

```
drove executor appinstances [-h] [--sort {0,1,2,3,4,5}] [--reverse] executor-id
```
###### Positional Arguments

`executor-id` - Executor id for which info is to be shown

###### Arguments

```
  --sort {0,1,2,3,4,5}, -s {0,1,2,3,4,5}
                        Sort output by column
  --reverse, -r         Sort in reverse order
```

##### tasks

Show tasks running on this executor

```
drove executor tasks [-h] [--sort {0,1,2,3,4,5}] [--reverse] executor-id
```

###### Positional Arguments

`executor-id` - Executor id for which info is to be shown

###### Named Arguments
```
  --sort {0,1,2,3,4,5}, -s {0,1,2,3,4,5}
                        Sort output by column
  --reverse, -r         Sort in reverse order
```


### cluster
---
Drove cluster related commands

```
drove cluster [-h] {ping,summary,leader,endpoints,events} ...
```

#### Sub-commands

##### ping

Ping the cluster

```
drove cluster ping [-h]
```

##### summary

Show cluster summary

```
drove cluster summary [-h]
```

##### leader

Show leader for cluster
```
drove cluster leader [-h]
```
##### endpoints

Show all exposed endpoints
```
drove cluster endpoints [-h] [--vhost VHOST]
```

###### Named Arguments

```
  --vhost VHOST, -v VHOST
                        Show details only for the specific vhost
```

##### events

Events on the cluster

```
drove cluster events [-h] [--follow] [--type TYPE] [--count COUNT] [--textfmt TEXTFMT]
```

###### Named Arguments

```
  --follow, -f          Follow events (Press CTRL-C to kill)
  --type TYPE, -t TYPE  Output events of only the matching type
  --count COUNT, -c COUNT
                        Fetch <count> events at a time.
  --textfmt TEXTFMT, -s TEXTFMT
                        Use the format string to print message
                        Default: “{type: <25} | {id: <36} | {time: <20} | {metadata}”
```

### apps
---
Drove application related commands

```
drove apps [-h] {list,summary,spec,create,destroy,deploy,scale,suspend,restart,cancelop} ...
```
#### Sub-commands

##### list

List all applications

```
drove apps list [-h] [--sort {0,1,2,3,4,5,6,7,8}] [--reverse]
```

###### Named Arguments

```
  --sort {0,1,2,3,4,5,6,7,8}, -s {0,1,2,3,4,5,6,7,8}
                        Sort output by column
  --reverse, -r         Sort in reverse order
```

##### summary

Show a summary for an application
```
drove apps summary [-h] app-id
```
###### Positional Arguments

`app-id` - Application ID

##### spec

Print the raw json spec for an application
```
drove apps spec [-h] app-id
```
###### Positional Arguments

`app-id` - Application ID

##### create

Create application on cluster
```
drove apps create [-h] spec-file
```
###### Positional Arguments

`spec-file` - JSON spec file for the application

##### destroy

Destroy an app with zero instances
```
drove apps destroy [-h] app-id
```
###### Positional Arguments

`app-id` - Application ID

##### deploy

Deploy new app instances.
```
drove apps deploy [-h] [--parallelism PARALLELISM] [--timeout TIMEOUT] app-id instances
```
###### Positional Arguments

`app-id` - Application ID
`instances` - Number of new instances to be created

###### Named Arguments

```
  --parallelism PARALLELISM, -p PARALLELISM
                        Number of parallel threads to be used to execute operation (default: 1)
  --timeout TIMEOUT, -t TIMEOUT
                        Timeout for the operation on the cluster (default: 5 minutes)
  --wait, -w            Wait to ensure instance count is reached
```
##### scale

Scale app to required instances. Will increase or decrease instances on the cluster to match this number

```
drove apps scale [-h] [--parallelism PARALLELISM] [--timeout TIMEOUT] app-id instances
```
###### Positional Arguments

`app-id` - Application ID
`instances` - Number of instances. Setting this to 0 will suspend the app

###### Named Arguments

```
  --parallelism PARALLELISM, -p PARALLELISM
                        Number of parallel threads to be used to execute operation (default: 1)
  --timeout TIMEOUT, -t TIMEOUT
                        Timeout for the operation on the cluster (default: 5 minutes)
  --wait, -w            Wait to ensure instance count is reached
```

##### suspend

Suspend the app
```
drove apps suspend [-h] [--parallelism PARALLELISM] [--timeout TIMEOUT] app-id
```
###### Positional Arguments[¶](#Positional%20Arguments_repeat9 "Link to this heading")

`app-id` - Application ID

###### Named Arguments

```
  --parallelism PARALLELISM, -p PARALLELISM
                        Number of parallel threads to be used to execute operation (default: 1)
  --timeout TIMEOUT, -t TIMEOUT
                        Timeout for the operation on the cluster (default: 5 minutes)
  --wait, -w            Wait to ensure all instances are suspended
```

##### restart

Restart am existing app instances.

```
drove apps restart [-h] [--parallelism PARALLELISM] [--timeout TIMEOUT] app-id
```

###### Positional Arguments

`app-id` - Application ID

###### Named Arguments
```
  --parallelism PARALLELISM, -p PARALLELISM
                        Number of parallel threads to be used to execute operation (default: 1)
  --timeout TIMEOUT, -t TIMEOUT
                        Timeout for the operation on the cluster (default: 5 minutes)
  --wait, -w            Wait to ensure all instances are replaced
```
##### cancelop

Cancel current operation
```
drove apps cancelop [-h] app-id
```
###### Positional Arguments
`app-id` - Application ID

### appinstances
---
Drove application instance related commands
```
drove appinstances [-h] {list,info,logs,tail,download,replace,kill} ...
```
#### Sub-commands

##### list

List all application instances
```
drove appinstances list [-h] [--old] [--sort {0,1,2,3,4,5}] [--reverse] app-id
```
###### Positional Arguments
`app-id` - Application ID

###### Named Arguments

```
  --parallelism PARALLELISM, -p PARALLELISM
                        Number of parallel threads to be used to execute operation (default: 1)
  --timeout TIMEOUT, -t TIMEOUT
                        Timeout for the operation on the cluster (default: 5 minutes)
```
##### info

Print details for an application instance
```
drove appinstances info [-h] app-id instance-id
```
###### Positional Arguments
`app-id` - Application ID
`instance-id` - Application Instance ID

##### logs

Print list of logs for application instance
```
drove appinstances logs [-h] app-id instance-id
```
###### Positional Arguments

`app-id` - Application ID
`instance-id` - Application Instance ID

##### tail

Tail log for application instance
```
drove appinstances tail [-h] [--file FILE] app-id instance-id
```
###### Positional Arguments

`app-id` - Application ID
`instance-id` - Application Instance ID

###### Named Arguments

```
  --file FILE, -f FILE  Log filename to tail. Default is to tail output.log
```

##### download

Download log for application instance
```
drove appinstances download [-h] [--out OUT] app-id instance-id file
```
###### Positional Arguments

`app-id` - Application ID
`instance-id` - Application Instance ID
`file` - Log filename to download

###### Named Arguments
```
--out, -o Filename to download to. Default is the same filename as provided.
```
##### replace

Replace specific app instances with fresh instances
```
drove appinstances replace [-h] [--parallelism PARALLELISM] [--timeout TIMEOUT] app-id instance-id [instance-id ...]
```
###### Positional Arguments
`app-id` - Application ID
`instance-id` - Application Instance IDs

###### Named Arguments
```
  --parallelism PARALLELISM, -p PARALLELISM
                        Number of parallel threads to be used to execute operation (default: 1)
  --timeout TIMEOUT, -t TIMEOUT
                        Timeout for the operation on the cluster (default: 5 minutes)
  --wait, -w            Wait to ensure all instances are replaced
```

##### kill

Kill specific app instances
```
drove appinstances kill [-h] [--parallelism PARALLELISM] [--timeout TIMEOUT] app-id instance-id [instance-id ...]
```
###### Positional Arguments
`app-id` - Application ID
`instance-id` - Application Instance IDs

###### Named Arguments

```
  --parallelism PARALLELISM, -p PARALLELISM
                        Number of parallel threads to be used to execute operation
  --timeout TIMEOUT, -t TIMEOUT
                        Timeout for the operation on the cluster (default: 5 minutes)
  --wait, -w            Wait to ensure all instances are killed
```
### tasks
---
Drove task related commands
```
drove tasks [-h] {list,show,logs,tail,download} ...
```
#### Sub-commands

##### list

List all active tasks
```
drove tasks list [-h] [--app APP] [--sort {0,1,2,3,4,5,6,7,8}] [--reverse]
```
###### Named Arguments
```
  --app APP, -a APP     Show tasks only for the given source app
  --sort {0,1,2,3,4,5,6,7,8}, -s {0,1,2,3,4,5,6,7,8}
                        Sort output by column
  --reverse, -r         Sort in reverse order
```
##### show

Shows details about a task
```
drove tasks show [-h] source-app task-id
```
###### Positional Arguments
`source-app` - Name of the Drove application that started the task
`task-id` - Task ID

##### logs

Print list of logs for task
```
drove tasks logs [-h] source-app task-id
```
###### Positional Arguments
`source-app` - Name of the Drove application that started the task
`task-id` - Task ID

##### tail

Tail log for task
```
drove tasks tail [-h] [--file FILE] source-app task-id
```
###### Positional Arguments
`source-app` - Name of the Drove application that started the task
`task-id` - Task ID

###### Named Arguments

```
  --file FILE, -f FILE  Log filename to tail. Default is to tail output.log
```
##### download

Download log for task

```
drove tasks download [-h] [--out OUT] source-app task-id file
```
###### Positional Arguments
`source-app` - Name of the Drove application that started the task
`task-id` - Task ID
`file` - Log filename to download

###### Named Arguments

```
  --out OUT, -o OUT  Filename to download to. Default is the same filename as provided.
```

©2024, Santanu Sinha.