import unittest
from dataclasses import dataclass

from ai.consultation.context import build_reference_info_block


@dataclass
class FakeChunk:
    text: str
    source: str | None = None


class BuildReferenceInfoBlockTest(unittest.TestCase):
    def test_none_when_no_chunks(self) -> None:
        self.assertIsNone(build_reference_info_block(None))
        self.assertIsNone(build_reference_info_block([]))

    def test_none_when_chunks_are_all_empty_text(self) -> None:
        self.assertIsNone(build_reference_info_block([FakeChunk(text="   ")]))

    def test_includes_only_provided_chunk_text(self) -> None:
        block = build_reference_info_block([FakeChunk(text="두통은 다양한 원인으로 발생합니다.", source="샘플 문서")])
        self.assertIn("[참고 의료 정보]", block)
        self.assertIn("두통은 다양한 원인으로 발생합니다.", block)
        self.assertIn("샘플 문서", block)

    def test_respects_max_chunks(self) -> None:
        chunks = [FakeChunk(text=f"내용 {i}") for i in range(10)]
        block = build_reference_info_block(chunks, max_chunks=2)
        self.assertIn("[문서 1]", block)
        self.assertIn("[문서 2]", block)
        self.assertNotIn("[문서 3]", block)

    def test_truncates_long_chunk_text(self) -> None:
        block = build_reference_info_block([FakeChunk(text="가" * 2000)], max_chars_per_chunk=100)
        # 잘린 표시(…)가 있어야 하고, 원문 그대로 2000자가 다 들어가면 안 된다.
        self.assertIn("…", block)
        self.assertLess(len(block), 2000)


if __name__ == "__main__":
    unittest.main()
