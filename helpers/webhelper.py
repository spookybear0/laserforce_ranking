from sanic import Request

def get_post(request: Request):
    data = request.form
    for key in data:
        data[key] = data[key][0]
    return data