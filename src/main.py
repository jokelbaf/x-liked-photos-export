import asyncio
import argparse
import sys
import typing
import logging
import json
import yarl
import os
import pathlib

import aiohttp
import rookiepy
from tqdm.auto import tqdm


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] [%(levelname)s]: %(message)s")

URL = "https://x.com/i/api/graphql/U1iuEM9U-e3QXOIkqOFAyw/Likes?"
"""The URL to fetch data from."""

HEADERS: typing.Mapping[str, str] = {
    "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
}
"""Default headers appliable to all requests."""

QUERY: typing.Dict[str, typing.Dict[str, typing.Any]] = {
    "variables": {
        "userId": "1646623670968754176",
        "count": 100,
        "includePromotedContent": False,
        "withClientEventToken": False,
        "withBirdwatchNotes":False,
        "withVoice": True,
        "withV2Timeline": True
    },
    "features": {
        "rweb_tipjar_consumption_enabled": True,
        "responsive_web_graphql_exclude_directive_enabled": True,
        "verified_phone_label_enabled": False,
        "creator_subscriptions_tweet_preview_api_enabled": True,
        "responsive_web_graphql_timeline_navigation_enabled": True,
        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
        "communities_web_enable_tweet_community_results_fetch": True,
        "c9s_tweet_anatomy_moderator_badge_enabled": True,
        "articles_preview_enabled": True,
        "tweetypie_unmention_optimization_enabled": True,
        "responsive_web_edit_tweet_api_enabled": True,
        "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
        "view_counts_everywhere_api_enabled": True,
        "longform_notetweets_consumption_enabled": True,
        "responsive_web_twitter_article_tweet_consumption_enabled": True,
        "tweet_awards_web_tipping_enabled": False,
        "creator_subscriptions_quote_tweet_preview_enabled": False,
        "freedom_of_speech_not_reach_fetch_enabled": True,
        "standardized_nudges_misinfo": True,
        "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
        "rweb_video_timestamps_enabled": True,
        "longform_notetweets_rich_text_read_enabled": True,
        "longform_notetweets_inline_media_enabled": True,
        "responsive_web_enhance_cards_enabled": False
    },
    "fieldToggles": {
        "withArticlePlainText": False
    }
}
"""GraphQL query to fetch liked tweets."""


def get_query(
    data: typing.Dict[str, typing.Dict[str, typing.Any]],
    *,
    cursor: str | None = None,
) -> typing.Dict[str, str]:
    """Obtain query.
    
    :param data: The data to convert to a query.
    :return: The query.
    """
    return {
        key: json.dumps(
            {"cursor": cursor, **value} if key == "variables" and cursor is not None else value,
            separators=(",", ":")
        )
        for key, value in data.items()
    }


def find_values_by_key(data: typing.Dict[str, typing.Any], target_key: str) -> typing.List[str]:
    """Recursively searches through a dictionary and returns an array of all values 
    associated with the specified key.

    :param data: The dictionary to search through.
    :param target_key: The key to search for.
    :return: A list of values associated with the specified key.
    """
    results: typing.Sequence[str] = []

    def search(d: typing.Dict[str, typing.Any] | typing.Sequence[typing.Any]) -> None:
        if isinstance(d, dict):
            for key, value in d.items():
                if key == target_key:
                    results.append(value)
                search(value)
        elif isinstance(d, list):
            for item in d:
                search(item)

    search(data)
    return results


def cookies_to_mapping(cookies: rookiepy.CookieList) -> typing.Mapping[str, typing.Any]:
    """Convert rookiepy cookies to a mapping.
    
    :param cookies: The cookies to convert.
    :return: The cookies as a mapping.
    """
    return {cookie["name"]: cookie["value"] for cookie in cookies if cookie["domain"] == ".x.com"}


def get_bottom_cursor(data: typing.Dict[str, typing.Any]) -> str | None:
    """Get the bottom cursor.
    
    :param data: The data to search for the bottom cursor.
    :return: The bottom cursor if found.
    """

    def search(d: typing.Dict[str, typing.Any] | typing.Sequence[typing.Any]) -> None:
        if isinstance(d, dict):
            if d.get("cursorType") == "Bottom":
                return d.get("value")
            for value in d.values():
                if result := search(value):
                    return result
        elif isinstance(d, list):
            for item in d:
                if result := search(item):
                    return result

    return search(data)


async def collect_images_urls(
    cookies: typing.Mapping[str, str] | str,
    token: str,
    *,
    cursor: str | None = None,
    progress: tqdm,  # type: ignore[reportUnknownParameterType]
) -> typing.List[str]:
    """Collect images URLs.
    
    :param cookies: The cookies to use.
    :param token: The token to use.
    :return: The images URLs.
    """
    query = get_query(QUERY, cursor=cursor)
    url = yarl.URL(URL).with_query(query)
    async with (
        aiohttp.ClientSession(
            headers={
                **HEADERS,
                "x-csrf-token": token,
                **({"cookie": HEADERS["cookie"]} if isinstance(cookies, str) else {}),
            },
            cookies=cookies if isinstance(cookies, dict) else None
        ) as session,
        session.get(url) as response
    ):
        if not response.ok:
            logger.error(f"Failed to fetch data: {response.status}")
            sys.exit(1)

        data = await response.json()
        images = find_values_by_key(data, "media_url_https")

        progress.update(len(images))

        if (cursor := get_bottom_cursor(data)) and len(images) != 0:
            more_images = await collect_images_urls(
                cookies, token, cursor=cursor, progress=progress
            )
            images = images + more_images

        return images


def save_to_file(images: typing.List[str], path: pathlib.Path) -> None:
    """Save images urls to a file.
    
    :param data: The data to save.
    :param path: The path to save the data to.
    """
    with open(path / "data.json", "w") as f:
        json.dump(images, f, indent=4)


async def download_images(images: typing.List[str], path: pathlib.Path) -> None:
    """Download images.
    
    :param images: The images to download.
    :param path: The path to download the images to.
    """
    async with aiohttp.ClientSession() as session:
        for image in tqdm(images, desc="Downloading images", unit=""):
            async with session.get(image) as response:
                data = await response.read()
                with open(path / pathlib.Path(image).name, "wb") as f:
                    f.write(data)


def dir_path(string: str) -> pathlib.Path:
    """Check if a path is a directory.
    
    :param string: The path to check.
    :return: The path if it is a directory.
    """
    if os.path.isdir(string):
        return pathlib.Path(string)
    else:
        raise NotADirectoryError(string)


def get_args() -> argparse.Namespace:
    """Parse arguments.
    
    :return: The parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="A simple tool that allows you download all your liked photos from X (Twitter)."
    )
    parser.add_argument(
        "--cookies", "-c", 
        type=str, 
        help="Raw 'Cookie' header. If not passed, reads cookies from your browsers."
    )
    parser.add_argument(
        "--token", 
        type=str, 
        required=True, 
        help="'x-csrf-token' copied from your browser network tab"
    )
    parser.add_argument(
        "--download", 
        action="store_true", 
        default=False, 
        help="Whether to download extracted images to your machine."
    )
    parser.add_argument(
        "--path", 
        type=dir_path, 
        help="Location for the script output."
    )
    try:
        return parser.parse_args()
    except NotADirectoryError:
        parser.error("The path provided is not a directory.")


async def main() -> None:
    """Entry point."""
    args = get_args()
    cookies = args.cookies or cookies_to_mapping(rookiepy.load())

    progress = tqdm(desc="Fetching images", unit="")
    images = await collect_images_urls(cookies, args.token, progress=progress)
    progress.close()

    save_to_file(images, args.path or pathlib.Path.cwd())

    if args.download:
        await download_images(images, args.path)

    logger.info("Report success")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
