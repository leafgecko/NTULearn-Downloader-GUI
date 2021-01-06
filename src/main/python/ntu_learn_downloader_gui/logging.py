from ntu_learn_downloader_gui.networking import post_error, post_successful_download


class Logger:
    def __init__(self, appctxt):
        self.version = appctxt.build_settings["version"]
        self.test_mode = appctxt.build_settings.get("test_mode", False)

    def log_successful_download(self, numDownloaded):
        post_successful_download(numDownloaded, self.version, self.test_mode)

    def log_error(self, error_trace: str):
        post_error(error_trace, self.version, self.test_mode)
