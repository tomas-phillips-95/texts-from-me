import base64
import datetime
import json
import os
from http.server import BaseHTTPRequestHandler
from typing import Any
from urllib.parse import urlparse

import requests
from twilio.twiml.messaging_response import MessagingResponse


class GithubClient:
    def __init__(self) -> None:
        self.token = os.getenv("GITHUB_TOKEN")
        self.repo_name = "tomas-phillips-95/my-texts"
        self.file_path = f"data/{self._get_file_name()}"
        self.branch = "main"

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }

    def _get_file_name(self) -> str:
        current_datetime = datetime.datetime.now()
        formatted_string = current_datetime.strftime("%B-%Y")
        return f"{formatted_string}.json"

    def _get_url(self) -> str:
        return f"https://api.github.com/repos/{self.repo_name}/contents/{self.file_path}?ref={self.branch}"

    def _get_file_data(self) -> dict[str, str]:
        response = requests.get(self._get_url(), headers=self._get_headers())
        response.raise_for_status()
        return response.json()

    def _decode_file_content(self, file_data: dict[str, str]) -> list[dict[str, Any]]:
        content = base64.b64decode(file_data["content"]).decode("utf-8")
        if not content:
            return []
        content_json = json.loads(content)
        return content_json

    def _encode_file_content(self, content_json: list[dict[str, Any]]) -> str:
        content = json.dumps(content_json)
        return base64.b64encode(content.encode("utf-8")).decode("utf-8")

    def _commit_file(self, sha: str | None, content: str) -> None:
        payload = {
            "message": "Append SMS message",
            "content": content,
            "sha": sha,
            "branch": self.branch,
        }
        response = requests.put(
            self._get_url(), json=payload, headers=self._get_headers()
        )
        response.raise_for_status()

    def update_github_file(self, message) -> None:
        """Update a file in a GitHub repository with the given message."""
        sha: str | None = None
        content_json = []

        try:
            file_data = self._get_file_data()
            content_json = self._decode_file_content(file_data)
            sha = file_data["sha"]
        except requests.exceptions.HTTPError as e:
            if e.response and e.response.status_code == 404:
                pass
            else:
                raise

        content_json.append(
            {"message": message, "timestamp": str(datetime.datetime.now())}
        )
        updated_content = self._encode_file_content(content_json)
        self._commit_file(sha, updated_content)


client = GithubClient()


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write("Hello, world!".encode("utf-8"))
        return


class SMSHandler(BaseHTTPRequestHandler):
    client = GithubClient()

    def do_POST(self):
        # Parse the incoming data
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)
        data = urlparse.parse_qs(post_data.decode())

        incoming_msg = data.get("Body", [""])[0].strip()
        resp = MessagingResponse()

        try:
            self.client.update_github_file(incoming_msg)
            resp.message("Message received :^)")
        except Exception as e:
            print(e)
            resp.message("Failed to save the message :^(")

        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(str(resp).encode("utf-8"))


if __name__ == "__main__":
    app.run()