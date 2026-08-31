import json
import unittest

import httpx

from ai.rag import RemoteEmbeddingError, RemoteEmbeddingProvider


class RemoteEmbeddingProviderTest(unittest.TestCase):
    def test_query_and_passage_contract_batching_and_normalization(self) -> None:
        received: list[dict] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            received.append(
                {
                    "payload": payload,
                    "authorization": request.headers.get("Authorization"),
                }
            )
            vector = [3.0, 4.0] + [0.0] * 1022
            return httpx.Response(
                200,
                json={
                    "model": payload["model"],
                    "dimensions": 1024,
                    "embeddings": [vector for _ in payload["texts"]],
                },
            )

        provider = _provider(httpx.MockTransport(handler), batch_size=2)
        passages = provider.embed_texts(["하나", "둘", "셋"])
        query = provider.embed_query("질문")

        self.assertEqual(len(passages), 3)
        self.assertAlmostEqual(passages[0][0], 0.6)
        self.assertAlmostEqual(passages[0][1], 0.8)
        self.assertAlmostEqual(query[0], 0.6)
        self.assertEqual(
            [item["payload"]["input_type"] for item in received],
            ["passage", "passage", "query"],
        )
        self.assertTrue(
            all(item["authorization"] == "Bearer secret-key" for item in received)
        )
        self.assertTrue(all(item["payload"]["model"] == "jina-v4" for item in received))

    def test_wrong_dimension_is_rejected(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "model": "jina-v4",
                    "dimensions": 128,
                    "embeddings": [[0.1] * 128],
                },
            )

        with self.assertRaises(RemoteEmbeddingError):
            _provider(httpx.MockTransport(handler)).embed_query("질문")

    def test_missing_configuration_is_rejected_before_request(self) -> None:
        provider = RemoteEmbeddingProvider(
            base_url="",
            api_key=None,
            model="jina-v4",
        )

        with self.assertRaises(RemoteEmbeddingError) as raised:
            provider.embed_query("질문")

        self.assertIn("EMBEDDING_REMOTE_BASE_URL", str(raised.exception))

    def test_upstream_body_is_not_exposed(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="secret upstream body")

        with self.assertRaises(RemoteEmbeddingError) as raised:
            _provider(httpx.MockTransport(handler)).embed_query("질문")

        self.assertNotIn("secret upstream", str(raised.exception))


def _provider(
    transport: httpx.BaseTransport,
    *,
    batch_size: int = 32,
) -> RemoteEmbeddingProvider:
    return RemoteEmbeddingProvider(
        base_url="https://embedding.test",
        api_key="secret-key",
        model="jina-v4",
        dimension=1024,
        timeout_seconds=5,
        batch_size=batch_size,
        transport=transport,
    )


if __name__ == "__main__":
    unittest.main()
