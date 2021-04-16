import requests
import jwt
import datetime
from time import time
from dotenv import dotenv_values

config = dotenv_values(".env")


def is_today_working_day():
    formatted_today_date = datetime.datetime.now().strftime("%Y%m%d")
    isdayoff_response = requests.get("https://isdayoff.ru/{}".format(formatted_today_date))
    return (isdayoff_response.status_code == 200) and (isdayoff_response.text == "0")


def generate_zoom_jwt():
    token = jwt.encode(
        {"iss": config["ZOOM_API_KEY"], "exp": time() + 5000},
        config["ZOOM_API_SECRET"],
        algorithm='HS256'
    )

    return token


def zoom_get_user_id(zoom_jwt):
    zoom_users_response = requests.get(
        "https://api.zoom.us/v2/users",
        headers={"Authorization": "Bearer {}".format(zoom_jwt)}
    )
    if zoom_users_response.status_code != 200:
        return None
    zoom_users_data = zoom_users_response.json()
    zoom_user = zoom_users_data["users"][0]
    return zoom_user["id"]


def zoom_create_meeting(topic, start_time, timezone, duration):
    zoom_jwt = generate_zoom_jwt()
    zoom_user_id = zoom_get_user_id(zoom_jwt)
    zoom_meeting_create_response = requests.post(
        "https://api.zoom.us/v2/users/{}/meetings".format(zoom_user_id),
        headers={"Authorization": "Bearer {}".format(zoom_jwt)},
        json={
            "topic": topic,
            "type": 2,
            "start_time": "{date}T{time}:00".format(
                date=datetime.datetime.now().strftime("%Y-%m-%d"),
                time=start_time
            ),
            "timezone": timezone,
            "duration": duration,
            "settings": {
                "join_before_host": True
            }
        }
    )
    if zoom_meeting_create_response.status_code != 201:
        return None
    print(zoom_meeting_create_response.json())
    return zoom_meeting_create_response.json()["join_url"]


def slack_send_message(token, channel, text):
    send_message_response = requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer {}".format(token)},
        data={"channel": channel, "text": text}
    )
    print(send_message_response.text)


if __name__ == '__main__':
    if not is_today_working_day():
        exit(0)

    zoom_meeting_url = zoom_create_meeting(
        topic=config["MEETING_NAME"],
        start_time=config["MEETING_TIME"],
        timezone=config["MEETING_TIMEZONE"],
        duration=config["MEETING_DURATION"]
    )
    if not zoom_meeting_url:
        exit(0)

    slack_send_message(token=config["SLACK_BOT_OAUTH_TOKEN"],
                       channel=config["SLACK_CHANNEL"],
                       text=config["MESSAGE_TEMPLATE"].format(time=config["MEETING_TIME"], url=zoom_meeting_url))
