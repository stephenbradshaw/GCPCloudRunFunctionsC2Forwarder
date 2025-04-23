import functions_framework
import os 
import requests
from flask import Response

DEBUG=os.getenv('DEBUG', False) 
TESTPATH=os.getenv('TESTPATH', '/b8af860c6c7f78d5cbcaa86c8f11b268cd0c0295')
PROTOCOL=os.getenv('PROTOCOL', 'http')

@functions_framework.http
def main(request):
    rpath = request.path
    if rpath == TESTPATH:
        return 'OK'
    
    host=os.getenv('DESTINATION')
    timeout = int(os.getenv('TIMEOUT', 20)) # override using TIMEOUT env variable
    path = f'{PROTOCOL}://{host}{rpath}'
    try:
        r = requests.request(request.method, path, params=request.args, stream=True, 
                            headers=dict(request.headers), allow_redirects=False, 
                            data=request.get_data(), timeout=timeout)
        def generate():
            for chunk in r.raw.stream(decode_content=False):
                yield chunk
        out = Response(generate(), headers=dict(r.raw.headers))
        out.status_code = r.status_code
        return out
    except Exception as e:
        # change these responses to remove indicators
        if DEBUG:
            return f'Error: {str(e)}'
        else:
            return 'Error'
        

