import requests

SERVER_HOST_URL = "http://ntulearndownloader.xyz"


def post_error(error_trace: str, version: str, test_mode: bool):
    data = {"trace": error_trace, "version": version}
    if test_mode:
        print("DEBUG: POST /error, data:", data)
    requests.post(SERVER_HOST_URL + "/error", data=data)


def post_successful_download(numDownloaded: int, version: str, test_mode: bool):
    data = {"numFiles": numDownloaded, "version": version}
    if test_mode:
        print("DEBUG: POST /download, data:", data)
    else:
        requests.post(SERVER_HOST_URL + "/download", data=data)