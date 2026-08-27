import unittest

from ai.rag.chunking import chunk_text, count_tokens, is_garbage


class ChunkingTest(unittest.TestCase):
    def test_count_tokens_uses_generic_tokenizer(self) -> None:
        self.assertEqual(count_tokens(""), 0)
        self.assertGreater(count_tokens("두통이 계속 있어요"), 0)

    def test_is_garbage_detects_symbol_only_text(self) -> None:
        self.assertTrue(is_garbage("   "))
        self.assertTrue(is_garbage("---***///"))
        self.assertFalse(is_garbage("두통"))

    def test_short_text_becomes_single_chunk(self) -> None:
        chunks = chunk_text("환자는 3일 전부터 두통을 호소하고 있습니다.")
        self.assertEqual(len(chunks), 1)
        self.assertGreater(chunks[0].token_count, 0)

    def test_long_text_is_split_within_token_budget(self) -> None:
        sentence = "환자는 두통과 어지럼증을 호소하고 있습니다. "
        long_text = sentence * 100
        chunks = chunk_text(long_text, max_tokens=50, overlap_tokens=10)

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(chunk.token_count, 60)  # overlap 붙어도 살짝 여유

    def test_paragraph_boundary_is_never_merged_across(self) -> None:
        text = "첫 번째 단락 내용입니다.\n\n두 번째 단락 내용입니다."
        chunks = chunk_text(text, max_tokens=300, overlap_tokens=0)

        joined = " ".join(c.text for c in chunks)
        self.assertIn("첫 번째", joined)
        self.assertIn("두 번째", joined)

    def test_garbage_only_input_returns_no_chunks(self) -> None:
        self.assertEqual(chunk_text("   ...---   "), [])


if __name__ == "__main__":
    unittest.main()
