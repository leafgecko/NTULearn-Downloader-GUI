import requests

SERVER_HOST_URL = "http://ntulearndownloader.xyz"


class Logger:
    def __init__(self, appctxt):
        self.version = appctxt.build_settings["version"]

    def log_successful_download(self, numDownloaded):
        data = {"numFiles": numDownloaded, "version": self.version}
        requests.post(SERVER_HOST_URL + "/download", data=data)

    def log_error(self, error_trace: str):
        data = {"trace": error_trace, "version": self.version}
        requests.post(SERVER_HOST_URL + "/error", data=data)
