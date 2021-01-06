import requests
from ntu_learn_downloader_gui.structs import VersionResult
from typing import Optional
import json
import traceback

SERVER_HOST_URL = "http://ntulearndownloader.xyz"
# SERVER_HOST_URL = "http://localhost:5000"


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


def get_latest_version(version: str, test_mode: bool) -> Optional[VersionResult]:
    if test_mode:
        raise ValueError("This method should be mocked")
    response = requests.get(SERVER_HOST_URL + "/releases/latest")
    if response.status_code != 200:
        post_error(
            f"GET /releases/latest failed with {response.status_code}: {str(response.content)}",
            version,
            test_mode,
        )
        return None
    try:
        data = json.loads(response.content)
        return VersionResult(
            version=data["version"],
            date=data["date"],
            link=data["link"],
            title=data["title"],
            content=data["content"],
        )
    except Exception:
        trace = traceback.format_exc()
        error_message = "\n".join(
            [
                "parsing result of GET /releases/latest failed",
                f"data: {data}",
                f"trace: {trace}",
            ]
        )
        post_error(error_message, version, test_mode)
    return None

