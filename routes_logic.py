from __main__ import config
from flask import render_template, redirect, abort, Response
import routes_file_request
import tmdb_api
import database_queries as dbq
from scan_library import scanning_and_threading, return_scan_percentage
from sessions import create_new_session
from transcoding import ffprobe_getduration
from flask_paginate import Pagination, get_page_args


"""
Default render template. Adds context to the template that needs to be on every page.
"""


def default_render_template(template, **context):
    return render_template(template, library=config["library"], **context,)


"""
Media filters
"""


def get_media_filters(request, library_name, genre=None):
    orderby_number = request.form.get("orderby")
    search_keyword = request.form.get("search")

    media_filter = [
        "popularity DESC",
        "popularity ASC",
        "vote_average DESC",
        "vote_average ASC",
        "release_date DESC",
        "release_date ASC",
        "title DESC",
        "title ASC",
    ]

    try:
        orderby = media_filter[int(orderby_number)]
    except Exception:
        orderby = media_filter[0]

    if genre is None:
        genre = "all"

    if search_keyword is None:
        search_keyword = ""
    else:
        search_keyword = search_keyword.strip()

    genres = dbq.library_genres(library_name)

    media_filters = {
        "orderby": {"selected": orderby,},
        "genres": {"selected": genre, "list": genres},
        "search": {"available": True, "keyword": search_keyword},
        "library_name": library_name,
    }

    return media_filters


"""
All the functions that are used in routes.py
"""


def home():
    movie = dbq.get_popular_movies()
    tvshow = dbq.get_popular_tvshows()

    return default_render_template(
        "home/popular-j2.html",
        selected="home",
        movie=movie,
        tvshow=tvshow,
        goback=False,
    )


def media(request, library_name, genre, **context):

    media_filters = get_media_filters(request, library_name, genre)
    media = dbq.library(
        library_name,
        media_filters["orderby"]["selected"],
        genre,
        media_filters["search"]["keyword"],
    )

    if media != "Invalid Library Type":

        """
        Pagination
        """

        page, per_page, offset = get_page_args(
            page_parameter="page", per_page_parameter="per_page"
        )
        offset = (page - 1) * 100
        per_page = 100
        media_pagination = media[offset : offset + per_page]
        total = len(media)
        context["pagination"] = Pagination(page=page, per_page=per_page, total=total)
        context["page"] = page
        context["per_page"] = per_page

        return default_render_template(
            "library/pagination-j2.html",
            selected=library_name,
            library_name=library_name,
            media=media_pagination,
            media_filters=media_filters,
            goback=(genre),
            **context,
        )
    else:
        return abort(404)


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
    scanning_and_threading()
    percentage = return_scan_percentage()
    auto_refresh = percentage != 100
    return default_render_template(
        "library/scanning-j2.html",
        selected="scan",
        percentage=return_scan_percentage(),
        auto_refresh=auto_refresh,
    )


def page_not_found(error):
    return default_render_template("error/404-j2.html")

