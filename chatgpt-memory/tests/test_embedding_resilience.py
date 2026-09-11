import json
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from chatgpt_archive import embed, post_json  # noqa: E402


class EmbeddingResilienceTests(unittest.TestCase):
    def test_embed_prefers_modern_endpoint_with_truncation(self):
        with patch("chatgpt_archive.post_json", return_value={"embeddings": [[1.0, 0.0]]}) as request:
            result = embed("hello", model="nomic-embed-text", host="http://ollama:11434")

        self.assertEqual(result, [1.0, 0.0])
        request.assert_called_once_with(
            "http://ollama:11434/api/embed",
            {"model": "nomic-embed-text", "input": "hello", "truncate": True},
        )

    def test_embed_falls_back_to_legacy_endpoint_when_modern_is_unavailable(self):
        unavailable = urllib.error.HTTPError(
            "http://ollama:11434/api/embed", 404, "not found", hdrs=None, fp=None
        )
        with patch(
            "chatgpt_archive.post_json",
            side_effect=[unavailable, {"embedding": [0.5, 0.5]}],
        ) as request:
            result = embed("hello", model="nomic-embed-text", host="http://ollama:11434")

        self.assertEqual(result, [0.5, 0.5])
        self.assertEqual(
            request.call_args_list,
            [
                call(
                    "http://ollama:11434/api/embed",
                    {"model": "nomic-embed-text", "input": "hello", "truncate": True},
                ),
                call(
                    "http://ollama:11434/api/embeddings",
                    {"model": "nomic-embed-text", "prompt": "hello"},
                ),
            ],
        )

    def test_post_json_retries_transient_server_error(self):
        failure = urllib.error.HTTPError(
            "http://ollama:11434/api/embed", 500, "server error", hdrs=None, fp=None
        )
        response = MagicMock()
        response.__enter__.return_value = response
        response.__exit__.return_value = False
        response.read.return_value = json.dumps({"embeddings": [[1.0]]}).encode()

        with patch(
            "chatgpt_archive.urllib.request.urlopen", side_effect=[failure, response]
        ) as urlopen, patch("chatgpt_archive.time.sleep") as sleep:
            result = post_json(
                "http://ollama:11434/api/embed",
                {"model": "nomic-embed-text", "input": "hello", "truncate": True},
            )

        self.assertEqual(result, {"embeddings": [[1.0]]})
        self.assertEqual(urlopen.call_count, 2)
        sleep.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
