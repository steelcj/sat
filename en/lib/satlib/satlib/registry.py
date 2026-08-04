"""satlib.registry — cached external authority sources.

Generic cache machinery implementing the resolution sequence of the
SAT Language Validation and Offline Registry Cache Specification
(v0.1.0, sections 2.2-2.5). The machinery is source-agnostic: a
CachedSource descriptor names the authority, its URL, its cache
location, and its staleness policy. The IANA Language Subtag Registry
is the first consumer (see satlib.language); further authorities are
added by defining a descriptor, not by changing this module.

Resolution sequence (spec section 2.4):

    cache present + not stale    -> use cache, no network request
    cache present + stale        -> attempt update
                                    success: use updated cache
                                    failure: warn, use stale cache
    cache absent + network up    -> download, write cache, use cache
    cache absent + network down  -> require explicit operator
                                    confirmation (spec section 2.5)
"""

from __future__ import annotations

import datetime as _dt
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

import yaml

__all__ = [
    "CachedSource",
    "CacheStatus",
    "CacheResult",
    "CacheUnavailableError",
    "RegistryCache",
    "default_fetcher",
]

# A fetcher takes a URL and returns the raw bytes of the resource.
# It is injectable so tests never touch the network.
Fetcher = Callable[[str], bytes]

# A file-date extractor derives the authority's own publication date
# (e.g. the IANA File-Date header) from raw content. Optional because
# not every source declares one.
FileDateExtractor = Callable[[bytes], Optional[str]]

_FETCH_TIMEOUT_SECONDS = 30.0


def default_fetcher(url: str) -> bytes:
    """Fetch raw bytes over HTTP(S). Raises OSError on any failure."""
    with urllib.request.urlopen(url, timeout=_FETCH_TIMEOUT_SECONDS) as response:
        return response.read()


@dataclass(frozen=True)
class CachedSource:
    """Descriptor for one cached external authority."""

    name: str
    source_url: str
    cache_path: Path
    staleness_days: int = 30
    file_date_extractor: Optional[FileDateExtractor] = None

    @property
    def meta_path(self) -> Path:
        """Freshness metadata sits beside the cache: <stem>-meta.yml."""
        return self.cache_path.with_name(self.cache_path.stem + "-meta.yml")


class CacheStatus(Enum):
    """How the returned content was obtained."""

    FRESH = "fresh"                        # cache present, within threshold
    STALE_UPDATED = "stale-updated"        # was stale, update succeeded
    STALE_USED = "stale-used"              # was stale, update failed, stale used
    DOWNLOADED = "downloaded"              # cache was absent, download succeeded
    ABSENT_UNVALIDATED = "absent-unvalidated"  # offline, operator confirmed


@dataclass
class CacheResult:
    """Outcome of a resolution: content plus the facts about it.

    content is None only for ABSENT_UNVALIDATED, in which case callers
    must apply the non-authority model to every tag (spec section 2.5)
    and record the unvalidated status in any authority note.
    """

    content: Optional[bytes]
    status: CacheStatus
    file_date: Optional[str] = None
    warnings: list[str] = field(default_factory=list)

    @property
    def validated(self) -> bool:
        return self.content is not None


class CacheUnavailableError(RuntimeError):
    """Cache absent and network unavailable, without operator consent.

    Raised so the calling tool can present the spec section 2.5
    warning and require --offline-confirm or an abort. No records may
    be written while this condition stands unconfirmed.
    """

    def __init__(self, source: CachedSource):
        self.source = source
        super().__init__(
            f"{source.name}: cache is absent and the source is unreachable. "
            f"Validation cannot be performed. Pass offline_confirmed=True "
            f"only on explicit operator instruction (--offline-confirm)."
        )


class RegistryCache:
    """Resolve a CachedSource per the spec's resolution sequence."""

    def __init__(
        self,
        source: CachedSource,
        fetcher: Fetcher = default_fetcher,
        today: Callable[[], _dt.date] = _dt.date.today,
    ):
        self._source = source
        self._fetch = fetcher
        self._today = today

    # -- public ----------------------------------------------------------

    def resolve(self, offline_confirmed: bool = False) -> CacheResult:
        content = self._read_cache()
        meta = self._read_meta()

        if content is not None:
            if not self._is_stale(meta):
                return CacheResult(
                    content=content,
                    status=CacheStatus.FRESH,
                    file_date=meta.get("file_date"),
                )
            return self._resolve_stale(content, meta)

        return self._resolve_absent(offline_confirmed)

    # -- resolution branches ---------------------------------------------

    def _resolve_stale(self, stale_content: bytes, meta: dict) -> CacheResult:
        try:
            fresh = self._fetch(self._source.source_url)
        except OSError as exc:
            self._touch_last_checked(meta)
            return CacheResult(
                content=stale_content,
                status=CacheStatus.STALE_USED,
                file_date=meta.get("file_date"),
                warnings=[
                    f"{self._source.name}: cache is stale and the update "
                    f"attempt failed ({exc}). Using the stale cache; a "
                    f"stale cache is always better than no validation."
                ],
            )
        file_date = self._write_cache(fresh)
        return CacheResult(
            content=fresh, status=CacheStatus.STALE_UPDATED, file_date=file_date
        )

    def _resolve_absent(self, offline_confirmed: bool) -> CacheResult:
        try:
            fresh = self._fetch(self._source.source_url)
        except OSError:
            if not offline_confirmed:
                raise CacheUnavailableError(self._source)
            return CacheResult(
                content=None,
                status=CacheStatus.ABSENT_UNVALIDATED,
                warnings=[
                    f"{self._source.name}: proceeding without validation on "
                    f"explicit operator confirmation. All records must note "
                    f"unvalidated status (sat:authority: none)."
                ],
            )
        file_date = self._write_cache(fresh)
        return CacheResult(
            content=fresh, status=CacheStatus.DOWNLOADED, file_date=file_date
        )

    # -- cache and metadata I/O --------------------------------------------

    def _read_cache(self) -> Optional[bytes]:
        try:
            return self._source.cache_path.read_bytes()
        except FileNotFoundError:
            return None

    def _write_cache(self, content: bytes) -> Optional[str]:
        self._source.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._source.cache_path.write_bytes(content)

        file_date = None
        if self._source.file_date_extractor is not None:
            file_date = self._source.file_date_extractor(content)

        today = self._today().isoformat()
        self._write_meta(
            {
                "file_date": file_date,
                "last_checked": today,
                "last_updated": today,
                "cache_source": self._source.source_url,
            }
        )
        return file_date

    def _read_meta(self) -> dict:
        try:
            loaded = yaml.safe_load(self._source.meta_path.read_text("utf-8"))
            return loaded if isinstance(loaded, dict) else {}
        except FileNotFoundError:
            return {}

    def _write_meta(self, meta: dict) -> None:
        self._source.meta_path.parent.mkdir(parents=True, exist_ok=True)
        self._source.meta_path.write_text(
            yaml.safe_dump(meta, sort_keys=False), "utf-8"
        )

    def _touch_last_checked(self, meta: dict) -> None:
        meta = dict(meta)
        meta["last_checked"] = self._today().isoformat()
        self._write_meta(meta)

    # -- staleness ---------------------------------------------------------

    def _is_stale(self, meta: dict) -> bool:
        """A cache with no readable last_updated is treated as stale.

        Unknown age must trigger an update attempt rather than being
        trusted as fresh; if the attempt fails the cache is still used
        (stale cache beats no validation).
        """
        last_updated = meta.get("last_updated")
        if not last_updated:
            return True
        try:
            updated = _dt.date.fromisoformat(str(last_updated))
        except ValueError:
            return True
        age = self._today() - updated
        return age.days > self._source.staleness_days
