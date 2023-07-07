import json
from typing import Any, Dict
import urllib.request

DEFAULT_HEADERS: Dict[str, str] = {
    "Accept": "application/json",
    "User_Agent": "python",
}


def req(
    url: str,
    data: Dict = None,
    params: Dict = None,
    headers: Dict = None,
    method: str = "GET",
    json_data: bool = True,
):
    data = data or {}
    params = params or {}
    headers = headers or {}
    headers.update(DEFAULT_HEADERS)
    method = method.upper()
    if method == "GET":
        params = {**params, **data}
        data = None
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True, safe="/")
    request_data = None
    if data:
        request_data = urllib.parse.urlencode(data).encode()
        if json_data:
            request_data = json.dumps(data).encode()
            headers["Content-Type"] = "application/json; charset=UTF-8"
    httprequest = urllib.request.Request(
        url, data=request_data, headers=headers, method=method
    )
    response: Dict[str, Any] = {}
    try:
        with urllib.request.urlopen(httprequest) as httpresponse:
            response = {
                "headers": dict(httpresponse.headers),
                "status": httpresponse.status,
                "body": json.loads(
                    httpresponse.read().decode(
                        httpresponse.headers.get_content_charset("utf-8")
                    )
                ),
            }
    except urllib.error.HTTPError as e:
        response = {
            "headers": dict(e.headers),
            "status": e.code,
            "body": str(e.reason),
        }
    return response
