import datetime
import droveclient
import json
import tabulate
import time

def print_dict(data: dict, level: int = 0):
    for key, value in data.items():
        print(level * 4 * " ", end='')
        if type(value) is dict and not len(dict(value)) == 0:
            print(f"{key: <30}")
            print_dict(value, level + 1)
        elif type(value) is list and all(isinstance(n, dict) for n in value):
            print(f"{key: <30}")
            for item in value:
                print_dict(item, level + 1)
                print()
        else:
            print(f"{key: <30}{value}")

def print_json(data: dict):
    print(json.dumps(data, indent = 4))

def print_table(headers: list, data: list):
    print(tabulate.tabulate(data, headers=headers))

def print_dict_table(data: dict, headers: list = None):
    if headers:
        print(tabulate.tabulate(data, headers=headers))
    else:
        print(tabulate.tabulate(data, headers="keys"))
                            
def to_date(epoch: int) -> str:
    date = datetime.datetime.fromtimestamp(epoch/1000)
    return date.strftime("%d/%m/%Y, %H:%M:%S")

def now():
    return round(time.time() * 1000)

def populate_resources(raw: dict, output: dict):
    cpu_list = [r for r in raw.get("resources", list()) if r.get("type", "") == "CPU"]
    if len(cpu_list) > 0:
        output["CPU"] = ", ".join(["NUMA Node %s: Cores: %s" % (key, value) for (key, value) in cpu_list[0].get("cores", dict()).items()])
    memory_list = [r for r in raw.get("resources", list()) if r.get("type", "") == "MEMORY"]
    if len(memory_list) > 0:
        output["Memory (MB)"] = ", ".join(["NUMA Node %s: Cores: %s" % (key, value) for (key, value) in memory_list[0].get("memoryInMB", dict()).items()])

def list_logs(drove_client: droveclient.DroveClient, prefix: str, domain: str, id: str):
    data = drove_client.get_raw("/apis/v1/logfiles/{prefix}/{domain}/{id}/list".format(prefix=prefix, domain=domain, id=id))
    print_dict(data)

def tail_log(drove_client: droveclient.DroveClient, prefix: str, domain: str, id: str, file_name: str):
    offset:int = -1
    old_offset:int = -1
    while True:
        old_offset = offset
        data = drove_client.get_raw("/apis/v1/logfiles/{prefix}/{domain}/{id}/read/{name}?offset={offset}"
                                    .format(prefix=prefix, domain=domain, id=id, name=file_name, offset=offset))
        data_length = len(data["data"])
        if old_offset == -1:
            offset = int(data["offset"])
        else:
            offset = offset + data_length
        
        if data_length == 0:
            time.sleep(1) #Nothing available right now .. try a bit later. TODO: binary backoff overkill here?
        else:
            print(data["data"], end='')

def download_log(drove_client: droveclient.DroveClient, prefix: str, domain: str, id: str, file_name: str, outfilename: str):
    print("Downloading log to: " + outfilename)
    size = drove_client.get_to_file("/apis/v1/logfiles/{prefix}/{domain}/{id}/download/{name}"
                                    .format(prefix=prefix, domain=domain, id=id, name=file_name), outfilename)
    print("Downloaded size: {size:,} bytes".format(size = size))

def print_drove_error(e: droveclient.DroveException, print_raw: bool):
    printed = False
    if e.api_response != None:
        if "data" in e.api_response:
            if "message" in e.api_response:
                print("Error: [{code} - {status}] {message}.".format(message=e.api_response["message"], code=e.status_code, status=e.api_response["status"]))
                printed = True
            if "validationErrors" in e.api_response["data"]:
                print("Validation errors:")
                [print("  - " + err) for err in e.api_response["data"]["validationErrors"]]
                printed = True
        if print_raw:
            print("Raw Response: ")
            print_json(e.api_response)
    if printed == False:
        print("Error making Drove call: {error}".format(error = str(e)))
