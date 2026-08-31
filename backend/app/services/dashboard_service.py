"""관리자 대시보드 지표 집계 — `consultation_logs`를 읽기만 한다(쓰기는
`message.py`가 담당). 전부 집계 쿼리라 개별 사용자 식별 정보(이메일 등)는
응답에 절대 포함하지 않는다 — 특히 "사용자별 사용량"은 구간별 사용자 수
분포로만 노출한다(개인정보 보관 정책이 아직 미정이라, 지금은 익명 집계만
안전하다고 보고 개별 사용자 리스트는 만들지 않았다).

사용자 만족도(좋아요/싫어요)는 아직 그 기능 자체가 없어서 이 모듈에 없다 —
근거 없는 수치를 만들어내지 않는다(루트 CLAUDE.md "근거 없는 성능·정확도
주장 금지"). "오류율"도 별도 HTTP 오류 로그가 없어서 만들지 않았고, 대신
`fallback_rate`(LLM 호출이 실패해서 안전한 대체 응답으로 넘어간 비율)를
가장 가까운 지표로 쓴다.
"""
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.generated import AdminDocuments, ConsultationLogs, DocumentChunks

DEFAULT_TREND_DAYS = 14


@dataclass
class DashboardKpis:
    today_consultations: int
    active_users_today: int
    avg_response_time_ms: float | None
    rag_hit_rate: float | None
    emergency_count_today: int
    fallback_rate: float | None
    document_count: int
    chunk_count: int


@dataclass
class DailyPoint:
    date: str
    count: int


@dataclass
class ModelUsageStat:
    model_id: str
    total: int
    success: int
    success_rate: float


@dataclass
class UserUsageBucket:
    label: str
    user_count: int


@dataclass
class DashboardOverview:
    kpis: DashboardKpis
    daily_consultations: list[DailyPoint]
    emergency_trend: list[DailyPoint]
    model_usage: list[ModelUsageStat]
    user_usage_distribution: list[UserUsageBucket]


def _today_start() -> datetime:
    return datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)


def _count(db: Session, *conditions) -> int:
    stmt = select(func.count(ConsultationLogs.id))
    if conditions:
        stmt = stmt.where(*conditions)
    return db.scalar(stmt) or 0


def get_kpis(db: Session) -> DashboardKpis:
    today_start = _today_start()
    today_filter = ConsultationLogs.created_at >= today_start

    total_today = _count(db, today_filter)
    rag_hits_today = _count(db, today_filter, ConsultationLogs.rag_hit_count > 0)
    fallback_today = _count(db, today_filter, ConsultationLogs.is_fallback.is_(True))

    active_users_today = db.scalar(
        select(func.count(func.distinct(ConsultationLogs.user_id))).where(today_filter)
    ) or 0
    avg_response_time_ms = db.scalar(
        select(func.avg(ConsultationLogs.response_time_ms)).where(today_filter)
    )

    return DashboardKpis(
        today_consultations=total_today,
        active_users_today=active_users_today,
        avg_response_time_ms=float(avg_response_time_ms) if avg_response_time_ms is not None else None,
        # total_today가 0이면 "0%"가 아니라 "아직 데이터 없음"이 정확하므로 None을 반환한다.
        rag_hit_rate=(rag_hits_today / total_today) if total_today else None,
        emergency_count_today=_count(db, today_filter, ConsultationLogs.is_emergency.is_(True)),
        fallback_rate=(fallback_today / total_today) if total_today else None,
        document_count=db.scalar(select(func.count(AdminDocuments.id))) or 0,
        chunk_count=db.scalar(select(func.count(DocumentChunks.id))) or 0,
    )


def _daily_series(db: Session, *extra_conditions, days: int) -> list[DailyPoint]:
    """최근 `days`일간 하루 단위 카운트. 로그가 없는 날짜도 0으로 채워서
    프론트 라인 차트의 x축이 끊기지 않게 한다."""
    since = _today_start() - timedelta(days=days - 1)
    day_expr = func.date(ConsultationLogs.created_at)
    stmt = (
        select(day_expr.label("day"), func.count(ConsultationLogs.id))
        .where(ConsultationLogs.created_at >= since, *extra_conditions)
        .group_by(day_expr)
    )
    counts = {str(day): count for day, count in db.execute(stmt).all()}

    points: list[DailyPoint] = []
    for i in range(days):
        day = (since + timedelta(days=i)).date()
        points.append(DailyPoint(date=str(day), count=counts.get(str(day), 0)))
    return points


def get_daily_consultations(db: Session, days: int = DEFAULT_TREND_DAYS) -> list[DailyPoint]:
    return _daily_series(db, days=days)


def get_emergency_trend(db: Session, days: int = DEFAULT_TREND_DAYS) -> list[DailyPoint]:
    return _daily_series(db, ConsultationLogs.is_emergency.is_(True), days=days)


def get_model_usage(db: Session, days: int = DEFAULT_TREND_DAYS) -> list[ModelUsageStat]:
    """모델별 호출 수/성공 수. is_fallback=False면 성공으로 센다(응급 하드필터로
    LLM을 아예 안 부른 요청은 model_id가 없어서 여기 안 잡힌다)."""
    since = _today_start() - timedelta(days=days - 1)
    success_expr = case((ConsultationLogs.is_fallback.is_(False), 1), else_=0)
    stmt = (
        select(
            ConsultationLogs.model_id,
            func.count(ConsultationLogs.id),
            func.sum(success_expr),
        )
        .where(ConsultationLogs.created_at >= since, ConsultationLogs.model_id.is_not(None))
        .group_by(ConsultationLogs.model_id)
        .order_by(func.count(ConsultationLogs.id).desc())
    )

    stats: list[ModelUsageStat] = []
    for model_id, total, success in db.execute(stmt).all():
        total = total or 0
        success = int(success or 0)
        stats.append(
            ModelUsageStat(
                model_id=model_id,
                total=total,
                success=success,
                success_rate=(success / total) if total else 0.0,
            )
        )
    return stats


_USER_USAGE_BUCKETS = (
    ("1~5", 1, 5),
    ("6~10", 6, 10),
    ("11~20", 11, 20),
    ("21+", 21, None),
)


def get_user_usage_distribution(db: Session, days: int = DEFAULT_TREND_DAYS) -> list[UserUsageBucket]:
    """사용자별 상담 횟수를 구간별 인원 수로만 집계한다 — 개별 사용자 식별 정보
    (이메일 등)는 절대 응답에 안 넣는다. 개인정보 보관 정책이 정해지기 전까지는
    이 익명 집계 형태가 안전하다고 보고 이렇게 설계했다."""
    since = _today_start() - timedelta(days=days - 1)
    per_user = (
        select(ConsultationLogs.user_id, func.count(ConsultationLogs.id).label("cnt"))
        .where(ConsultationLogs.created_at >= since)
        .group_by(ConsultationLogs.user_id)
        .subquery()
    )
    counts = [row[0] for row in db.execute(select(per_user.c.cnt)).all()]

    buckets = []
    for label, low, high in _USER_USAGE_BUCKETS:
        n = sum(1 for c in counts if c >= low and (high is None or c <= high))
        buckets.append(UserUsageBucket(label=label, user_count=n))
    return buckets


def get_overview(db: Session, days: int = DEFAULT_TREND_DAYS) -> DashboardOverview:
    return DashboardOverview(
        kpis=get_kpis(db),
        daily_consultations=get_daily_consultations(db, days),
        emergency_trend=get_emergency_trend(db, days),
        model_usage=get_model_usage(db, days),
        user_usage_distribution=get_user_usage_distribution(db, days),
    )
