from __main__ import config
from flask import render_template, redirect
import routes_file_request
import tmdb_api
import database_queries as dbq
from scan_library import scan
from sessions import create_new_session
from transcoding import ffprobe_getduration


"""
Default render template. Adds context to the template that needs to be on every page.
"""


def default_render_template(template, **context):
    return render_template(template, library=config["library"], **context)


"""
Media filters
"""


def get_media_filters(request, library_name, genre=None):
    orderby_number = request.form.get("orderby")

    media_filter = [
        "popularity DESC",
        "popularity ASC",
        "vote_average DESC",
        "vote_average ASC",
        "release_date DESC",
        "release_date ASC",
        "title ASC",
        "title DESC",
    ]

    try:
        orderby = media_filter[int(orderby_number)]
    except Exception:
        orderby = media_filter[0]

    if genre is None:
        genre = "all"

    genres = dbq.library_genres(library_name)

    media_filters = {
        "orderby": {"selected": orderby,},
        "genres": {"selected": genre, "list": genres},
        "search": True,
        "library_name": library_name,
    }

    return media_filters


"""
All the functions that are used in routes.py
"""


def home():
    movie = tmdb_api.get_popular_movies()
    tvshow = tmdb_api.get_popular_tvshows()
    goback = False

    return default_render_template(
        "home/popular-j2.html",
        selected="home",
        movie=movie,
        tvshow=tvshow,
        goback=False,
    )


def media(request, library_name, genre):

    media_filters = get_media_filters(request, library_name, genre)
    media = dbq.library(library_name, media_filters["orderby"]["selected"], genre)

    return default_render_template(
        "library/media-j2.html",
        selected=library_name,
        media=media,
        media_filters=media_filters,
        goback=(genre),
    )


def overview(library_name, video_id, season_number, episode_number, **context):

    content_type = dbq.library_content_type(library_name)

    if content_type == "movie":
        template = "overview/buttons-j2.html"
        context["overview"] = dbq.library_overview("movie", video_id)

    elif content_type == "tv":
        context["overview"] = dbq.library_overview(
            "tv", video_id, season_number, episode_number
        )

        if episode_number:
            template = "overview/buttons-j2.html"
            context["episode"] = True
            context["genre_prefix"] = "../../../"

        elif season_number:
            template = "overview/episodes-j2.html"
            context["episode"] = dbq.library_overview_episodes(video_id, season_number)
            context["genre_prefix"] = "../../"

        else:
            template = "overview/seasons-j2.html"
            context["season"] = dbq.library_overview_seasons(video_id)

    return default_render_template(
        template, selected=library_name, goback=True, **context
    )


def trailer(library_name, video_id):
    trailer = dbq.library_overview_trailer(library_name, video_id)
    youtube = trailer["video"]
    video_title = f"""Trailer - {trailer["title"]}"""

    return render_template(
        "player/youtube-j2.html",
        sync=False,
        youtube=youtube,
        video_title=video_title,
        goback=True,
    )


def overview_play(
    request, library_name, video_id, season_number=None, episode_number=None
):

    transcoding = request.args.get("transcoding")
    redirect_url = f"""/video/"""
    available = dbq.media_path(video_id, season_number, episode_number)

    if available:
        if season_number:
            redirect_url += f"{video_id}/{season_number}/{episode_number}"
        else:
            redirect_url += f"{video_id}"

        session_id = create_new_session(video_id)

        if session_id:
            redirect_url += f"?session={session_id}"

        if transcoding:
            redirect_url += f"""&transcoding={request.args.get("transcoding")}"""

        return redirect(redirect_url)

    else:

        overview = tbq.library_overview(video_id, season_number, episode_number)

        return default_render_template(
            "overview/error.html",
            selected=library_name,
            overview=overview,
            error=f"Error - File not found",
            goback=True,
        )


def player_video(request, video_id, season_number=None, episode_number=None):

    session_id = request.args.get("session")
    transcoding = request.args.get("transcoding")

    path = dbq.media_path(video_id, season_number, episode_number)

    if season_number:
        meta = dbq.library_overview("tv", video_id)
        video_title = f"""{meta["title"]} - S{str(season_number).zfill(2)}E{str(episode_number).zfill(2)}"""
        video_id = f"{video_id}/{season_number}/{episode_number}"
    else:
        meta = dbq.library_overview("movie", video_id)
        video_title = f"""{meta["title"]}"""

    try:
        video_duration = ffprobe_getduration(path)
    except Exception:
        video_duration = 0
        print(f"Can not get duration of video:")

    return render_template(
        "player/player-j2.html",
        video_title=video_title,
        video_id=video_id,
        video_duration=video_duration,
        session_id=session_id,
        transcoding=transcoding,
        goback=True,
    )


def overview_tmdb(content_type, video_id):
    overview = tmdb_api.tmdb_overview(content_type, video_id)

    return default_render_template(
        "overview/buttons-j2.html",
        selected="home",
        overview=overview,
        goback=True,
        tmdb=True,
    )


def scan_library():
    scan()
    return "scan complete"
