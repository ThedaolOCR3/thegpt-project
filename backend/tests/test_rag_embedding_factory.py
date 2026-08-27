import unittest

from ai.rag import HashingEmbeddingProvider, SentenceTransformerEmbeddingProvider
from app.core.config import Settings
from app.core.rag_embedding import build_rag_embedding_provider


def _settings(**overrides) -> Settings:
    # 실제 .env를 안 읽고 필드만 오버라이드한 최소 Settings를 만든다.
    return Settings(_env_file=None, **overrides)


class BuildRagEmbeddingProviderTest(unittest.TestCase):
    def test_hashing_is_the_default(self) -> None:
        provider = build_rag_embedding_provider(_settings())
        self.assertIsInstance(provider, HashingEmbeddingProvider)

    def test_sentence_transformer_selected_by_name(self) -> None:
        provider = build_rag_embedding_provider(
            _settings(
                rag_embedding_provider="sentence_transformer",
                rag_embedding_model_name="BAAI/bge-m3",
            )
        )
        self.assertIsInstance(provider, SentenceTransformerEmbeddingProvider)
        self.assertEqual(provider.name, "BAAI/bge-m3")

    def test_sentence_transformer_without_model_name_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_rag_embedding_provider(_settings(rag_embedding_provider="sentence_transformer"))

    def test_unknown_provider_name_raises(self) -> None:
        with self.assertRaises(ValueError):
            build_rag_embedding_provider(_settings(rag_embedding_provider="does-not-exist"))


if __name__ == "__main__":
    unittest.main()
