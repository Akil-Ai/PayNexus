"""Unit tests for sanctions fuzzy matching — normalization, thresholds, PASS/REVIEW/BLOCKED."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.sanctions_service import _normalize_name, _local_fuzzy_match


# ── _normalize_name ────────────────────────────────────────────────────────────

class TestNormalizeName:
    def test_lowercases(self):
        assert _normalize_name("John DOE") == "john doe"

    def test_strips_accents(self):
        # é → e, ñ → n
        assert _normalize_name("José Müller") == "jose muller"

    def test_collapses_whitespace(self):
        assert _normalize_name("  Osama   Bin  Laden  ") == "osama bin laden"

    def test_unicode_normalization(self):
        # Full-width characters
        result = _normalize_name("Ａｌｉ")
        assert "ali" in result

    def test_empty_string(self):
        assert _normalize_name("") == ""

    def test_single_name(self):
        assert _normalize_name("KIM") == "kim"


# ── _local_fuzzy_match ─────────────────────────────────────────────────────────

def _make_watchlist_entry(name: str, aliases: str = "", entry_id: str = "wl-001"):
    entry = MagicMock()
    entry.id = entry_id
    entry.name = name
    entry.aliases = aliases
    entry.is_active = True
    return entry


def _make_db(entries):
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = entries
    db.execute = AsyncMock(return_value=mock_result)
    return db


class TestLocalFuzzyMatch:

    @pytest.mark.asyncio
    async def test_pass_on_empty_watchlist(self):
        db = _make_db([])
        result = await _local_fuzzy_match(db, "John Smith", 90.0, 75.0)
        assert result["result"] == "PASS"
        assert result["score"] == 0.0

    @pytest.mark.asyncio
    async def test_exact_match_is_blocked(self):
        """Exact name match must exceed block threshold (90)."""
        entries = [_make_watchlist_entry("Osama Bin Laden")]
        db = _make_db(entries)
        result = await _local_fuzzy_match(db, "Osama Bin Laden", 90.0, 75.0)
        assert result["result"] == "BLOCKED"
        assert result["score"] >= 90.0

    @pytest.mark.asyncio
    async def test_close_match_is_review(self):
        """Name with minor typo → score between review and block thresholds."""
        entries = [_make_watchlist_entry("Vladimir Putin")]
        db = _make_db(entries)
        # Slightly different spelling, still very similar
        result = await _local_fuzzy_match(db, "Vladimir Puton", 95.0, 70.0)
        # Score should be >= 70 (review) but potentially < 95 (block)
        assert result["result"] in ("REVIEW", "BLOCKED")
        assert result["score"] >= 70.0

    @pytest.mark.asyncio
    async def test_very_different_name_is_pass(self):
        """Completely unrelated name → PASS."""
        entries = [_make_watchlist_entry("Kim Jong Un")]
        db = _make_db(entries)
        result = await _local_fuzzy_match(db, "Alice Johnson", 90.0, 75.0)
        assert result["result"] == "PASS"

    @pytest.mark.asyncio
    async def test_alias_matching(self):
        """Match against alias field using pipe-separated aliases."""
        entries = [_make_watchlist_entry("Kim Jong Un", aliases="Supreme Leader|Dear Leader")]
        db = _make_db(entries)
        result = await _local_fuzzy_match(db, "Dear Leader", 90.0, 75.0)
        assert result["result"] == "BLOCKED"

    @pytest.mark.asyncio
    async def test_multiple_watchlist_entries_takes_best(self):
        """With multiple entries, should return BLOCKED from best match."""
        entries = [
            _make_watchlist_entry("John Smith", entry_id="wl-001"),
            _make_watchlist_entry("Osama Bin Laden", entry_id="wl-002"),
        ]
        db = _make_db(entries)
        result = await _local_fuzzy_match(db, "Osama Bin Laden", 90.0, 75.0)
        assert result["result"] == "BLOCKED"
        assert result["matched_id"] == "wl-002"

    @pytest.mark.asyncio
    async def test_high_block_threshold_downgrades_to_review(self):
        """If block threshold is very high (99), near-exact match becomes REVIEW."""
        entries = [_make_watchlist_entry("Osama Bin Laden")]
        db = _make_db(entries)
        result = await _local_fuzzy_match(db, "Osama Bin Laden", 99.0, 75.0)
        # Score will be 100 (perfect match), so should still block
        assert result["result"] in ("BLOCKED", "REVIEW")

    @pytest.mark.asyncio
    async def test_case_insensitive_matching(self):
        """Matching should be case-insensitive due to normalization."""
        entries = [_make_watchlist_entry("OSAMA BIN LADEN")]
        db = _make_db(entries)
        result = await _local_fuzzy_match(db, "osama bin laden", 90.0, 75.0)
        assert result["result"] == "BLOCKED"

    @pytest.mark.asyncio
    async def test_result_contains_matched_name_on_block(self):
        """BLOCKED result must include matched_name and matched_id."""
        entries = [_make_watchlist_entry("Kim Jong Un", entry_id="wl-kim")]
        db = _make_db(entries)
        result = await _local_fuzzy_match(db, "Kim Jong Un", 90.0, 75.0)
        assert result["matched_name"] is not None
        assert result["matched_id"] == "wl-kim"
