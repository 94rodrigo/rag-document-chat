from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.config import get_settings
from app.domain.auth.models import Plan
from app.domain.billing.models import UsageAction
from app.domain.billing.service import UsageLimitService, _plan_limits
from app.shared.exceptions import (
    DocumentLimitExceededError,
    QueryLimitExceededError,
    StorageLimitExceededError,
    UsageLimitExceededError,
)
from tests.conftest import (
    FakeAnonRepository,
    FakeAnonSession,
    FakeDocumentRepository,
    FakeUsageRepository,
    FakeUser,
    FakeUserRepository,
)

settings = get_settings()

FREE_DOCS, FREE_QUERIES, FREE_STORAGE = _plan_limits(Plan.free)


def build_service(
    user: FakeUser | None = None,
    doc_count: int = 0,
    storage_used: int = 0,
    queries_used: int = 0,
    anon_sessions: dict[str, FakeAnonSession] | None = None,
) -> UsageLimitService:
    users = FakeUserRepository([user] if user else [])
    docs = FakeDocumentRepository(count=doc_count, total_size=storage_used)
    period = datetime.now(UTC).strftime("%Y-%m")
    usage = FakeUsageRepository(
        {(user.id, str(UsageAction.query), period): queries_used} if user else {}
    )
    anon = FakeAnonRepository(anon_sessions or {})
    return UsageLimitService(
        user_repo=users, doc_repo=docs, usage_repo=usage, anon_repo=anon
    )


class TestPlanLimits:
    def test_free_plan_is_capped(self) -> None:
        docs, queries, storage = _plan_limits(Plan.free)
        assert (docs, queries, storage) == (10, 100, 52_428_800)

    def test_pro_plan_has_unlimited_documents_but_capped_queries(self) -> None:
        docs, queries, storage = _plan_limits(Plan.pro)
        assert docs == -1
        assert queries == 2_000
        assert storage == 10_737_418_240

    def test_enterprise_plan_is_unlimited(self) -> None:
        assert _plan_limits(Plan.enterprise) == (-1, -1, -1)

    def test_unknown_plan_falls_back_to_free(self) -> None:
        assert _plan_limits("something-else") == _plan_limits(Plan.free)


class TestDocumentLimit:
    async def test_free_user_at_document_limit_is_blocked(self, free_user) -> None:
        svc = build_service(user=free_user, doc_count=FREE_DOCS)

        with pytest.raises(DocumentLimitExceededError):
            await svc.assert_can_upload(free_user.id, file_size=1_000)

    async def test_free_user_below_document_limit_is_allowed(self, free_user) -> None:
        svc = build_service(user=free_user, doc_count=FREE_DOCS - 1)

        await svc.assert_can_upload(free_user.id, file_size=1_000)

    async def test_pro_user_has_no_document_ceiling(self, pro_user) -> None:
        svc = build_service(user=pro_user, doc_count=100_000)

        await svc.assert_can_upload(pro_user.id, file_size=1_000)

    async def test_document_limit_error_is_a_usage_limit_error(self, free_user) -> None:
        svc = build_service(user=free_user, doc_count=FREE_DOCS)

        with pytest.raises(UsageLimitExceededError) as exc:
            await svc.assert_can_upload(free_user.id, file_size=1)

        assert exc.value.status_code == 429
        assert exc.value.error_code == "DOCUMENT_LIMIT_EXCEEDED"


class TestStorageLimit:
    async def test_upload_exceeding_storage_quota_is_blocked(self, free_user) -> None:
        svc = build_service(user=free_user, storage_used=FREE_STORAGE - 100)

        with pytest.raises(StorageLimitExceededError):
            await svc.assert_can_upload(free_user.id, file_size=101)

    async def test_upload_filling_quota_exactly_is_allowed(self, free_user) -> None:
        """The check is `used + size > limit`, so landing exactly on the limit passes."""
        svc = build_service(user=free_user, storage_used=FREE_STORAGE - 100)

        await svc.assert_can_upload(free_user.id, file_size=100)

    async def test_enterprise_user_has_no_storage_ceiling(self, enterprise_user) -> None:
        svc = build_service(user=enterprise_user, storage_used=10**15)

        await svc.assert_can_upload(enterprise_user.id, file_size=10**12)

    async def test_document_limit_takes_precedence_over_storage(self, free_user) -> None:
        svc = build_service(
            user=free_user, doc_count=FREE_DOCS, storage_used=FREE_STORAGE
        )

        with pytest.raises(DocumentLimitExceededError):
            await svc.assert_can_upload(free_user.id, file_size=10**9)


class TestQueryLimit:
    async def test_free_user_at_query_limit_is_blocked(self, free_user) -> None:
        svc = build_service(user=free_user, queries_used=FREE_QUERIES)

        with pytest.raises(QueryLimitExceededError):
            await svc.assert_can_query(free_user.id, anon_session_id=None)

    async def test_free_user_below_query_limit_is_allowed(self, free_user) -> None:
        svc = build_service(user=free_user, queries_used=FREE_QUERIES - 1)

        await svc.assert_can_query(free_user.id, anon_session_id=None)

    async def test_enterprise_user_has_no_query_ceiling(self, enterprise_user) -> None:
        svc = build_service(user=enterprise_user, queries_used=10**6)

        await svc.assert_can_query(enterprise_user.id, anon_session_id=None)

    async def test_request_with_no_identity_is_rejected(self) -> None:
        svc = build_service()

        with pytest.raises(QueryLimitExceededError):
            await svc.assert_can_query(user_id=None, anon_session_id=None)


class TestAnonymousQueryLimit:
    async def test_anonymous_session_at_limit_is_blocked(self) -> None:
        cap = settings.anon_session_max_queries
        svc = build_service(anon_sessions={"anon-1": FakeAnonSession(query_count=cap)})

        with pytest.raises(QueryLimitExceededError):
            await svc.assert_can_query(user_id=None, anon_session_id="anon-1")

    async def test_anonymous_session_below_limit_is_allowed(self) -> None:
        cap = settings.anon_session_max_queries
        svc = build_service(
            anon_sessions={"anon-1": FakeAnonSession(query_count=cap - 1)}
        )

        await svc.assert_can_query(user_id=None, anon_session_id="anon-1")

    async def test_unknown_anonymous_session_is_allowed_through(self) -> None:
        """A session with no row yet has spent no quota."""
        svc = build_service(anon_sessions={})

        await svc.assert_can_query(user_id=None, anon_session_id="never-seen")

    async def test_anonymous_path_wins_when_both_identities_present(
        self, free_user
    ) -> None:
        """An exhausted user still passes if an unexhausted anon session is supplied,
        because the anonymous branch returns before the user check runs."""
        svc = build_service(
            user=free_user,
            queries_used=FREE_QUERIES,
            anon_sessions={"anon-1": FakeAnonSession(query_count=0)},
        )

        await svc.assert_can_query(free_user.id, anon_session_id="anon-1")


class TestUnknownUserFailsOpen:
    async def test_upload_by_unknown_user_is_not_blocked(self) -> None:
        svc = build_service(user=None, doc_count=10**6)

        await svc.assert_can_upload("ghost", file_size=10**9)

    async def test_query_by_unknown_user_is_not_blocked(self) -> None:
        svc = build_service(user=None)

        await svc.assert_can_query("ghost", anon_session_id=None)


class TestUsageRecording:
    async def test_query_is_recorded_against_the_current_period(self, free_user) -> None:
        svc = build_service(user=free_user)
        period = datetime.now(UTC).strftime("%Y-%m")

        await svc.record_query(free_user.id, anon_session_id=None)

        assert svc._usage.increments == [(free_user.id, str(UsageAction.query), period)]

    async def test_anonymous_queries_are_not_recorded_in_usage(self) -> None:
        svc = build_service()

        await svc.record_query(user_id=None, anon_session_id="anon-1")

        assert svc._usage.increments == []

    async def test_recorded_query_counts_toward_the_limit(self, free_user) -> None:
        svc = build_service(user=free_user, queries_used=FREE_QUERIES - 1)

        await svc.assert_can_query(free_user.id, anon_session_id=None)
        await svc.record_query(free_user.id, anon_session_id=None)

        with pytest.raises(QueryLimitExceededError):
            await svc.assert_can_query(free_user.id, anon_session_id=None)


class TestUsageStats:
    async def test_stats_report_usage_against_plan_limits(self, free_user) -> None:
        svc = build_service(
            user=free_user, doc_count=3, storage_used=1_024, queries_used=7
        )

        stats = await svc.get_usage_stats(free_user.id)

        assert stats.documents_used == 3
        assert stats.documents_limit == FREE_DOCS
        assert stats.queries_used == 7
        assert stats.queries_limit == FREE_QUERIES
        assert stats.storage_used_bytes == 1_024
        assert stats.storage_limit_bytes == FREE_STORAGE
        assert stats.period_key == datetime.now(UTC).strftime("%Y-%m")

    async def test_unknown_user_is_reported_on_the_free_plan(self) -> None:
        svc = build_service(user=None)

        stats = await svc.get_usage_stats("ghost")

        assert stats.documents_limit == FREE_DOCS
        assert stats.queries_limit == FREE_QUERIES
