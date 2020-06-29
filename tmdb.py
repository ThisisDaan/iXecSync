from tmdbv3api import TMDb, Movie
import urllib.request
import pathlib

tmdb = TMDb()
tmdb.api_key = "8330115f9230acfdbe0e5470649f6602"
tmdb.language = "en"
tmdb.debug = True


def download_movie_poster(search_str, thumbnail_location):
    file = pathlib.Path(thumbnail_location)
    if file.exists() is False:
        video_name = search_str.split(" (")
        print(f"searching for {video_name[0]}")

        movie = Movie()
        search = movie.search(video_name[0])
        if search:
            url = f"https://image.tmdb.org/t/p/w500/{search[0].poster_path}"
            urllib.request.urlretrieve(url, thumbnail_location)

