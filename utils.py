import json

def get_param(param):
    param_file = open('parameters.txt')
    data = param_file.read()
    param_file.close()

    param_data = json.loads(data)
    if param in param_data:
        return param_data[param]

