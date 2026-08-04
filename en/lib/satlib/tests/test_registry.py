"""Tests for satlib.registry against spec sections 2.2-2.5."""

import datetime

import pytest
import yaml

from satlib.registry import (
    CachedSource,
    CacheStatus,
    CacheUnavailableError,
    RegistryCache,
)

CONTENT_V1 = b"File-Date: 2026-05-20\n%%\nType: language\nSubtag: en\n"
CONTENT_V2 = b"File-Date: 2026-06-20\n%%\nType: language\nSubtag: en\n"

TODAY = datetime.date(2026, 7, 9)


def extract(content: bytes):
    return content.decode().splitlines()[0].split(": ")[1]


def make_source(tmp_path, staleness_days=30):
    return CachedSource(
        name="test-source",
        source_url="https://example.invalid/registry",
        cache_path=tmp_path / "cache" / "test-registry.txt",
        staleness_days=staleness_days,
        file_date_extractor=extract,
    )


def make_cache(source, fetch_result=None, fetch_error=None):
    calls = []

    def fetcher(url):
        calls.append(url)
        if fetch_error is not None:
            raise fetch_error
        return fetch_result

    cache = RegistryCache(source, fetcher=fetcher, today=lambda: TODAY)
    return cache, calls


def write_cached(source, content, last_updated):
    source.cache_path.parent.mkdir(parents=True)
    source.cache_path.write_bytes(content)
    source.meta_path.write_text(yaml.safe_dump({
        "file_date": extract(content),
        "last_checked": last_updated,
        "last_updated": last_updated,
        "cache_source": source.source_url,
    }))


class TestResolutionSequence:
    """The four rows of the spec section 2.4 table."""

    def test_present_and_fresh_uses_cache_without_network(self, tmp_path):
        source = make_source(tmp_path)
        write_cached(source, CONTENT_V1, "2026-07-01")  # 8 days old
        cache, calls = make_cache(source, fetch_result=CONTENT_V2)

        result = cache.resolve()

        assert result.status is CacheStatus.FRESH
        assert result.content == CONTENT_V1
        assert result.file_date == "2026-05-20"
        assert calls == []  # no network request

    def test_present_and_stale_updates_on_success(self, tmp_path):
        source = make_source(tmp_path)
        write_cached(source, CONTENT_V1, "2026-05-25")  # 45 days old
        cache, calls = make_cache(source, fetch_result=CONTENT_V2)

        result = cache.resolve()

        assert result.status is CacheStatus.STALE_UPDATED
        assert result.content == CONTENT_V2
        assert result.file_date == "2026-06-20"
        assert source.cache_path.read_bytes() == CONTENT_V2
        meta = yaml.safe_load(source.meta_path.read_text())
        assert meta["last_updated"] == TODAY.isoformat()

    def test_present_and_stale_uses_stale_on_failure(self, tmp_path):
        source = make_source(tmp_path)
        write_cached(source, CONTENT_V1, "2026-05-25")
        cache, _ = make_cache(source, fetch_error=OSError("network down"))

        result = cache.resolve()

        assert result.status is CacheStatus.STALE_USED
        assert result.content == CONTENT_V1  # stale beats no validation
        assert result.warnings
        meta = yaml.safe_load(source.meta_path.read_text())
        assert meta["last_checked"] == TODAY.isoformat()
        assert meta["last_updated"] == "2026-05-25"  # unchanged: no success

    def test_absent_with_network_downloads_and_writes(self, tmp_path):
        source = make_source(tmp_path)
        cache, _ = make_cache(source, fetch_result=CONTENT_V2)

        result = cache.resolve()

        assert result.status is CacheStatus.DOWNLOADED
        assert result.content == CONTENT_V2
        assert source.cache_path.read_bytes() == CONTENT_V2
        assert source.meta_path.exists()

    def test_absent_and_offline_requires_confirmation(self, tmp_path):
        source = make_source(tmp_path)
        cache, _ = make_cache(source, fetch_error=OSError("network down"))

        with pytest.raises(CacheUnavailableError):
            cache.resolve()

    def test_absent_and_offline_confirmed_is_unvalidated(self, tmp_path):
        source = make_source(tmp_path)
        cache, _ = make_cache(source, fetch_error=OSError("network down"))

        result = cache.resolve(offline_confirmed=True)

        assert result.status is CacheStatus.ABSENT_UNVALIDATED
        assert result.content is None
        assert not result.validated
        assert result.warnings


class TestStaleness:
    def test_threshold_boundary_is_exclusive(self, tmp_path):
        # Exactly staleness_days old is not yet stale (> threshold, spec 2.3)
        source = make_source(tmp_path, staleness_days=30)
        write_cached(source, CONTENT_V1, "2026-06-09")  # exactly 30 days
        cache, calls = make_cache(source, fetch_result=CONTENT_V2)

        assert cache.resolve().status is CacheStatus.FRESH
        assert calls == []

    def test_missing_meta_treated_as_stale(self, tmp_path):
        source = make_source(tmp_path)
        source.cache_path.parent.mkdir(parents=True)
        source.cache_path.write_bytes(CONTENT_V1)  # cache without meta

        cache, calls = make_cache(source, fetch_result=CONTENT_V2)
        result = cache.resolve()

        assert result.status is CacheStatus.STALE_UPDATED
        assert calls  # unknown age triggered an update attempt

    def test_operator_configured_threshold_respected(self, tmp_path):
        source = make_source(tmp_path, staleness_days=90)
        write_cached(source, CONTENT_V1, "2026-05-25")  # 45 days old
        cache, calls = make_cache(source, fetch_result=CONTENT_V2)

        assert cache.resolve().status is CacheStatus.FRESH
        assert calls == []


class TestMetaFile:
    def test_meta_path_derived_from_cache_path(self, tmp_path):
        source = make_source(tmp_path)
        assert source.meta_path.name == "test-registry-meta.yml"
        assert source.meta_path.parent == source.cache_path.parent

    def test_meta_records_spec_fields(self, tmp_path):
        source = make_source(tmp_path)
        cache, _ = make_cache(source, fetch_result=CONTENT_V2)
        cache.resolve()

        meta = yaml.safe_load(source.meta_path.read_text())
        assert set(meta) == {
            "file_date", "last_checked", "last_updated", "cache_source",
        }
        assert meta["file_date"] == "2026-06-20"
        assert meta["cache_source"] == source.source_url
