import unittest
from datetime import date, timedelta
from unittest.mock import MagicMock

from app.services import dashboard_service


def _mock_execute_rows(db: MagicMock, rows: list[tuple]) -> None:
    db.execute.return_value.all.return_value = rows


class GetKpisTest(unittest.TestCase):
    def test_zero_total_today_yields_none_rates_not_zero(self) -> None:
        # 오늘 상담이 0건이면 rag_hit_rate/fallback_rate는 "0%"가 아니라 "아직
        # 데이터 없음"을 뜻하는 None이어야 한다 — 0%라고 하면 "검색이 다 실패했다"는
        # 것처럼 잘못 읽힐 수 있다.
        db = MagicMock()
        db.scalar.side_effect = [0, 0, 0, 0, None, 0, 3, 7]
        kpis = dashboard_service.get_kpis(db)

        self.assertEqual(kpis.today_consultations, 0)
        self.assertIsNone(kpis.rag_hit_rate)
        self.assertIsNone(kpis.fallback_rate)
        self.assertIsNone(kpis.avg_response_time_ms)
        self.assertEqual(kpis.document_count, 3)
        self.assertEqual(kpis.chunk_count, 7)

    def test_nonzero_total_computes_rates(self) -> None:
        # total_today=10, rag_hits=8, fallback=2 -> 80%/20%
        db = MagicMock()
        db.scalar.side_effect = [10, 8, 2, 5, 1234.5, 1, 3, 7]
        kpis = dashboard_service.get_kpis(db)

        self.assertEqual(kpis.today_consultations, 10)
        self.assertAlmostEqual(kpis.rag_hit_rate, 0.8)
        self.assertAlmostEqual(kpis.fallback_rate, 0.2)
        self.assertEqual(kpis.active_users_today, 5)
        self.assertEqual(kpis.avg_response_time_ms, 1234.5)
        self.assertEqual(kpis.emergency_count_today, 1)


class DailySeriesTest(unittest.TestCase):
    def test_missing_days_are_filled_with_zero(self) -> None:
        db = MagicMock()
        today = date.today()
        # 3일 중 가운데 하루만 데이터가 있다고 가정
        middle_day = today - timedelta(days=1)
        _mock_execute_rows(db, [(middle_day, 5)])

        points = dashboard_service.get_daily_consultations(db, days=3)

        self.assertEqual(len(points), 3)
        counts_by_date = {p.date: p.count for p in points}
        self.assertEqual(counts_by_date[str(middle_day)], 5)
        # 나머지 이틀은 로그가 없었으므로 0으로 채워져야 한다(차트 x축이 안 끊기게).
        zero_days = [c for d, c in counts_by_date.items() if d != str(middle_day)]
        self.assertEqual(zero_days, [0, 0])

    def test_points_are_in_chronological_order(self) -> None:
        db = MagicMock()
        _mock_execute_rows(db, [])
        points = dashboard_service.get_daily_consultations(db, days=5)

        dates = [p.date for p in points]
        self.assertEqual(dates, sorted(dates))


class ModelUsageTest(unittest.TestCase):
    def test_success_rate_computed_per_model(self) -> None:
        db = MagicMock()
        _mock_execute_rows(
            db,
            [
                ("medgemma-main", 10, 2),  # 10번 중 2번 성공(GPU 없어서 대부분 폴백 흉내)
                ("qwen-medical", 4, 4),
            ],
        )
        stats = dashboard_service.get_model_usage(db)

        by_model = {s.model_id: s for s in stats}
        self.assertAlmostEqual(by_model["medgemma-main"].success_rate, 0.2)
        self.assertAlmostEqual(by_model["qwen-medical"].success_rate, 1.0)

    def test_zero_total_does_not_raise_zero_division(self) -> None:
        db = MagicMock()
        _mock_execute_rows(db, [("llama-medical", 0, 0)])
        stats = dashboard_service.get_model_usage(db)

        self.assertEqual(stats[0].success_rate, 0.0)


class UserUsageDistributionTest(unittest.TestCase):
    def test_buckets_users_by_message_count(self) -> None:
        db = MagicMock()
        # 사용자별 상담 횟수: 3, 7, 15, 25, 30 -> 1~5:1명, 6~10:1명, 11~20:1명, 21+:2명
        _mock_execute_rows(db, [(3,), (7,), (15,), (25,), (30,)])
        buckets = dashboard_service.get_user_usage_distribution(db)

        by_label = {b.label: b.user_count for b in buckets}
        self.assertEqual(by_label["1~5"], 1)
        self.assertEqual(by_label["6~10"], 1)
        self.assertEqual(by_label["11~20"], 1)
        self.assertEqual(by_label["21+"], 2)

    def test_no_identifying_fields_are_returned(self) -> None:
        # 응답 구조 자체에 user_id/email 같은 개별 식별 필드가 없어야 한다 —
        # 익명 집계(구간별 인원 수)만 노출한다는 설계를 회귀 테스트로 고정.
        db = MagicMock()
        _mock_execute_rows(db, [(3,)])
        buckets = dashboard_service.get_user_usage_distribution(db)

        field_names = set(vars(buckets[0]).keys())
        self.assertEqual(field_names, {"label", "user_count"})


if __name__ == "__main__":
    unittest.main()
