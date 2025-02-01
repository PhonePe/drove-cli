<%!
    import json
%>
<%def name="dict_to_json(data, **kwargs)" filter="trim">
    ${json.dumps(data,
        indent=kwargs.get('indent', None),
        separators=(',', ':') if not kwargs.get('indent') else (', ', ': '),
        ensure_ascii=kwargs.get('ensure_ascii', False),
        default=str  # Handle non-serializable objects
    )}
</%def>

{
    "name": "${reader.read_str('name', 'App name', pattern='[a-zA-Z0-9\-]+', max_length=255)}",
    "version": "${reader.read_str('version','App Version', pattern='[0-9.]+')}",
    "type": "SERVICE",
    "executable": {
        "type": "DOCKER",
        "url": "${reader.read_str('container', 'Container URL', pattern='^(?:(?P<registry>[a-zA-Z0-9.-]+)(?::(?P<port>\d+))?/)?(?P<repository>[a-z0-9-_.\/]+)(?::(?P<tag>[a-zA-Z0-9-_.]+)|@sha256:(?P<digest>[a-f0-9]{64}))?$', max_length=2048)}",
        "dockerPullTimeout": "${reader.read_str('dockerPullTimeout','Container Fetch Timeout', default='300sec')}"
    },
    "exposedPorts": [
        {
            "name": "main",
            "port":  ${reader.read_int('port','Port to be exposed',min_value=1,default=8080)},
            "type": "${reader.read_choice("portType", "Type of port", ["TCP","HTTP","HTTPS"], default="HTTP")}"
        }
    ],
    "volumes": [],
    "resources": [
        {
            "type": "CPU",
            "count": ${reader.read_int("cores", "CPU Cores to be allocated", min_value=1, default=1)}
        },
        {
            "type": "MEMORY",
            "sizeInMB": ${reader.read_int("memory", "Memory in MB", min_value=10, default=128)}
        }
    ],
    "placementPolicy": {
        "type": "ANY"
    },
    "healthcheck": {
        "mode": {
            "type": "HTTP",
            "protocol": "HTTP",
            "portName": "main",
            "path": "${reader.read_url_path('healthCheckPath', 'Healthcheck URL Path', default='/')}",
            "verb": "GET",
            "successCodes": [ 200, 201, 202 ],
            "payload": "",
            "connectionTimeout": "1 second"
        },
        "timeout": "1 second",
        "interval": "5 seconds",
        "attempts": 3,
        "initialDelay": "0 seconds"
    },
    "readiness": {
        "mode": {
            "type": "HTTP",
            "protocol": "HTTP",
            "portName": "main",
            "path": "${reader.read_url_path('readinessCheckPath', 'Readiness Check URL Path', default='/')}",
            "verb": "GET",
            "successCodes": [ 200, 201, 202 ],
            "payload": "",
            "connectionTimeout": "1 second"
        },
        "timeout": "1 second",
        "interval": "3 seconds",
        "attempts": 3,
        "initialDelay": "10 seconds"
    },
    "tags": {},
    "env": ${dict_to_json(reader.read_str_kvs("env", "Environment variable"), indent = 4)}
    "exposureSpec": {
        "vhost": "${reader.read_str('vhost', 'Virtual Host to be exposed on the Gateway', pattern='[a-zA-Z0-9.]+', max_length=1024)}",
        "portName": "main",
        "mode": "ALL"
    },
    "preShutdown": {
        "hooks": [
            {
                "type": "HTTP",
                "protocol": "HTTP",
                "portName": "main",
                "path": "/",
                "verb": "GET",
                "successCodes": [
                    200
                ],
                "payload": "",
                "connectionTimeout": "1 second"
            }
        ],
        "waitBeforeKill": "3 seconds"
    }
}
