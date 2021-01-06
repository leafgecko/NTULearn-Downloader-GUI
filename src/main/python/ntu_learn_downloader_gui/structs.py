from typing import Tuple

class VersionResult:
    # TOOO move date to datetime type
    def __init__(self, version: str, date: str, link: str, title: str, content: str):
        self.version: Tuple[int, ...] = tuple(map(int, version.split('.')))
        self.date = date
        self.link = link
        self.title = title
        self.content = content