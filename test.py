from pathlib import Path
import json


root = Path(__file__).parent
with open(Path(root, "config.json")) as file:
    config = json.load(file)

from tmdb_api import search


class scan_library:
    def __init__(self, dir, content_type):
        self.dir = dir
        self.content_type = content_type
        self.files = []

    def scan(self):
        self.get_files_in_dir()
        self.scrape_file_data()
        self.download_tmdb_data()

    def get_files_in_dir(self):

        directory = Path(self.dir)

        file_types = [".mp4", ".mkv"]

        for file_type in file_types:
            for path in directory.rglob(f"*{file_type}"):
                media = Media()
                media.path = path
                self.files.append(media)

    def scrape_file_data(self):
        for media in self.files:
            self.scrape_title(media)
            self.scrape_release_date(media)
            self.scrape_media_folder(media)

            if self.content_type == "tv":
                self.scrape_season_and_episode(media)

    def scrape_title(self, media):

        name = media.path.parent.name

        if "(" in name:
            media.title = name.split(" (")[0]
        else:
            media.title = name

    def scrape_release_date(self, media):

        name = media.path.parent.name

        if "(" in name:
            media.release_date = name.split(" (")[1].replace(")", "")
        else:
            media.release_date = None

    def scrape_media_folder(self, media):

        if self.content_type == "movie":
            media.folder = media.path.parent.name
        else:
            # We assume that every episode file is in a season folder.
            # tvshow/season/media_file
            media.folder = media.path.parent.parent.name

    def scrape_season_and_episode(self, media):

        match = re.findall(r"S[0-9][0-9]E[0-9][0-9]", file.name)

        if match:
            if match[0][1] == "0":
                media.season_number = match[0][2]
            else:
                media.season_number = match[0][1:3]

            if match[0][-2] == "0":
                media.episode_number = match[0][-1]
            else:
                media.episode_number = match[0][-2:]

    def download_tmdb_data(self):
        for media in self.files:
            tmdb_data = search(self.content_type, media.title, media.release_date)

            if tmdb_data:

                """
                episode data exist or not
                if not
                episode get season data                
                else
                get data
                apply
                """

                # Saving the json
                media.tmdb_data["tv"] = tmdb_data

                # Getting the trailer
                tmdb_data["video"] = tmdb_api.trailer(self.content_type, media.id)


class Media:
    pass


d = scan_library(r"C:\Users\dfran\Documents\GitHub\iXecSync\video\-=Movies=-", "movie")
d.scan()
