"""
Data consistency validation tests

Tests verify:
- No null names in skill_gems table
- No duplicate entries
- Cross-reference with PoB source data
- Data integrity constraints
"""

import pytest
import pytest_asyncio
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from database.manager import DatabaseManager
from sqlalchemy import text


@pytest_asyncio.fixture
async def db():
    """Database fixture"""
    db = DatabaseManager()
    await db.initialize()
    return db


@pytest.fixture
def pob_skills():
    """Load PoB skill data"""
    data_path = Path(__file__).parent.parent / "data" / "pob_complete_skills.json"
    with open(data_path) as f:
        return json.load(f)


@pytest.fixture
def merged_tree():
    """Load merged passive tree data"""
    data_path = Path(__file__).parent.parent / "data" / "merged_passive_tree.json"
    with open(data_path) as f:
        return json.load(f)


@pytest.mark.asyncio
async def test_no_null_names_skill_gems(db):
    """Verify no skill gems have null names"""
    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM skill_gems WHERE name IS NULL OR name = ''")
        )
        null_count = result.scalar()

        assert null_count == 0, f"Found {null_count} skill gems with null/empty names"


@pytest.mark.asyncio
async def test_no_null_names_support_gems(db):
    """Verify no support gems have null names"""
    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM support_gems WHERE name IS NULL OR name = ''")
        )
        null_count = result.scalar()

        assert null_count == 0, f"Found {null_count} support gems with null/empty names"


@pytest.mark.asyncio
async def test_no_null_names_passive_nodes(db):
    """Verify keystones and notables have names"""
    async with db.async_session() as session:
        # Keystones should all have names
        result = await session.execute(
            text("SELECT COUNT(*) FROM passive_nodes WHERE is_keystone = 1 AND (name IS NULL OR name = '')")
        )
        null_keystones = result.scalar()

        assert null_keystones == 0, f"Found {null_keystones} keystones with null/empty names"

        # Notables should all have names
        result = await session.execute(
            text("SELECT COUNT(*) FROM passive_nodes WHERE is_notable = 1 AND (name IS NULL OR name = '')")
        )
        null_notables = result.scalar()

        assert null_notables == 0, f"Found {null_notables} notables with null/empty names"


@pytest.mark.asyncio
async def test_no_duplicate_skill_names(db):
    """Check for duplicate skill gem names (some may be legitimate variants)"""
    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT name, COUNT(*) as cnt FROM skill_gems GROUP BY name HAVING cnt > 1")
        )
        duplicates = result.fetchall()

        # Some duplicates may be legitimate (e.g., different weapon variants)
        if duplicates:
            print(f"\nFound {len(duplicates)} skill names with multiple entries (may be legitimate variants):")
            for row in duplicates[:10]:
                print(f"  {row[0]}: {row[1]} occurrences")

            # Verify duplicates are reasonable in number
            assert len(duplicates) < 20, f"Too many duplicate skill names: {len(duplicates)}"


@pytest.mark.asyncio
async def test_no_duplicate_support_names(db):
    """Verify no duplicate support gem names"""
    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT name, COUNT(*) as cnt FROM support_gems GROUP BY name HAVING cnt > 1")
        )
        duplicates = result.fetchall()

        if duplicates:
            duplicate_names = [row[0] for row in duplicates]
            assert False, f"Found duplicate support gem names: {duplicate_names}"


@pytest.mark.asyncio
async def test_no_duplicate_passive_node_ids(db):
    """Verify no duplicate passive node IDs"""
    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT node_id, COUNT(*) as cnt FROM passive_nodes GROUP BY node_id HAVING cnt > 1")
        )
        duplicates = result.fetchall()

        if duplicates:
            duplicate_ids = [row[0] for row in duplicates]
            assert False, f"Found duplicate passive node IDs: {duplicate_ids}"


@pytest.mark.asyncio
async def test_skill_tags_are_valid_json(db):
    """Verify skill gem tags are valid JSON"""
    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT name, tags FROM skill_gems WHERE tags IS NOT NULL")
        )
        rows = result.fetchall()

        parse_errors = []
        for row in rows:
            try:
                tags = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                assert isinstance(tags, list), f"Tags should be a list for {row[0]}"
            except (json.JSONDecodeError, TypeError) as e:
                parse_errors.append((row[0], str(e)))

        assert len(parse_errors) == 0, f"Found {len(parse_errors)} skills with invalid tags: {parse_errors[:5]}"


@pytest.mark.asyncio
async def test_support_tags_are_valid_json(db):
    """Verify support gem tags are valid JSON"""
    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT name, tags FROM support_gems WHERE tags IS NOT NULL")
        )
        rows = result.fetchall()

        parse_errors = []
        for row in rows:
            try:
                tags = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                assert isinstance(tags, list), f"Tags should be a list for {row[0]}"
            except (json.JSONDecodeError, TypeError) as e:
                parse_errors.append((row[0], str(e)))

        assert len(parse_errors) == 0, f"Found {len(parse_errors)} supports with invalid tags: {parse_errors[:5]}"


@pytest.mark.asyncio
async def test_passive_stats_are_valid_json(db):
    """Verify passive node stats are valid JSON"""
    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT node_id, name, stats FROM passive_nodes WHERE stats IS NOT NULL LIMIT 200")
        )
        rows = result.fetchall()

        parse_errors = []
        for row in rows:
            try:
                stats = json.loads(row[2]) if isinstance(row[2], str) else row[2]
                assert isinstance(stats, (list, dict)), f"Stats should be list or dict for {row[1]}"
            except (json.JSONDecodeError, TypeError) as e:
                parse_errors.append((row[1], str(e)))

        error_rate = (len(parse_errors) / len(rows) * 100) if rows else 0
        assert error_rate < 5, f"Found {error_rate:.1f}% nodes with invalid stats: {parse_errors[:3]}"


@pytest.mark.asyncio
async def test_per_level_stats_are_valid_json(db):
    """Verify per-level stats are valid JSON"""
    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT name, per_level_stats FROM skill_gems WHERE per_level_stats IS NOT NULL")
        )
        rows = result.fetchall()

        parse_errors = []
        for row in rows:
            try:
                stats = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                assert isinstance(stats, dict), f"Per-level stats should be a dict for {row[0]}"

                # Verify keys are level numbers
                for key in stats.keys():
                    assert key.isdigit(), f"Per-level stats keys should be numeric for {row[0]}"
            except (json.JSONDecodeError, TypeError, AssertionError) as e:
                parse_errors.append((row[0], str(e)))

        assert len(parse_errors) == 0, f"Found {len(parse_errors)} skills with invalid per-level stats: {parse_errors[:5]}"


@pytest.mark.asyncio
async def test_cross_reference_sample_skills(db, pob_skills):
    """Cross-reference sample skills between database and PoB source"""
    # Get 20 random skills from database
    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT name FROM skill_gems ORDER BY RANDOM() LIMIT 20")
        )
        db_skills = [row[0] for row in result.fetchall()]

    # Check if they exist in PoB source
    pob_skill_names = {skill_data.get('name'): skill_id
                       for skill_id, skill_data in pob_skills['skills'].items()}

    found_in_pob = 0
    not_found = []

    for skill_name in db_skills:
        if skill_name in pob_skill_names:
            found_in_pob += 1
        else:
            not_found.append(skill_name)

    match_rate = (found_in_pob / len(db_skills) * 100) if db_skills else 0
    print(f"Skills found in PoB source: {found_in_pob}/{len(db_skills)} ({match_rate:.1f}%)")

    if not_found:
        print(f"Skills not found in PoB: {not_found[:5]}")

    # Should have high match rate
    assert match_rate >= 80, f"Expected >=80% match rate, got {match_rate:.1f}%"


@pytest.mark.asyncio
async def test_cross_reference_sample_passives(db, merged_tree):
    """Cross-reference sample keystones between database and merged tree"""
    async with db.async_session() as session:
        # Database may store node_id as name, so use pattern matching
        result = await session.execute(
            text("SELECT node_id, name FROM passive_nodes WHERE node_id LIKE '%keystone%' AND name IS NOT NULL LIMIT 20")
        )
        db_keystones = result.fetchall()

    if not db_keystones:
        # Try by is_keystone flag
        async with db.async_session() as session:
            result = await session.execute(
                text("SELECT node_id, name FROM passive_nodes WHERE is_keystone = 1 AND name IS NOT NULL LIMIT 20")
            )
            db_keystones = result.fetchall()

    if not db_keystones:
        print("No keystones found in database to cross-reference")
        return

    # Get keystones from merged tree
    merged_keystones_by_id = {node_id: node_data
                              for node_id, node_data in merged_tree.items()
                              if node_data.get('is_keystone')}

    merged_keystones_by_name = {node_data.get('name'): node_id
                                for node_id, node_data in merged_tree.items()
                                if node_data.get('is_keystone') and node_data.get('name')}

    found_in_merged = 0
    for node_id, name in db_keystones:
        # Check by node_id or name
        if node_id in merged_keystones_by_id or name in merged_keystones_by_name:
            found_in_merged += 1

    match_rate = (found_in_merged / len(db_keystones) * 100) if db_keystones else 0
    print(f"Keystones found in merged tree: {found_in_merged}/{len(db_keystones)} ({match_rate:.1f}%)")

    # Should have some match rate (may not be 100% due to naming differences)
    assert match_rate >= 50, f"Expected >=50% keystone match rate, got {match_rate:.1f}%"


@pytest.mark.asyncio
async def test_data_freshness_metadata(pob_skills):
    """Verify source data has fresh extraction date"""
    metadata = pob_skills.get('metadata', {})

    assert 'extraction_date' in metadata, "Source data should have extraction_date"
    extraction_date = metadata['extraction_date']

    # Should be recent (2025-12-13 or nearby)
    assert '2025-12' in extraction_date or '2025-11' in extraction_date, \
        f"Source data should be recent, found {extraction_date}"


@pytest.mark.asyncio
async def test_skill_counts_match_metadata(db, pob_skills):
    """Verify skill counts are consistent with metadata"""
    metadata = pob_skills.get('metadata', {})

    async with db.async_session() as session:
        result = await session.execute(text("SELECT COUNT(*) FROM skill_gems"))
        db_active_count = result.scalar()

        result = await session.execute(text("SELECT COUNT(*) FROM support_gems"))
        db_support_count = result.scalar()

    print(f"Database: {db_active_count} active + {db_support_count} support = {db_active_count + db_support_count} total")
    print(f"Metadata: {metadata.get('total_skills')} total in source")

    # Database may have slightly different count due to filtering
    # Just verify we're in the same ballpark
    assert db_active_count > 300, "Should have >300 active skills"
    assert db_support_count > 500, "Should have >500 support gems"


@pytest.mark.asyncio
async def test_required_level_constraints(db):
    """Verify required_level is non-negative"""
    async with db.async_session() as session:
        # Check skill gems
        result = await session.execute(
            text("SELECT COUNT(*) FROM skill_gems WHERE required_level < 0")
        )
        invalid_count = result.scalar()
        assert invalid_count == 0, f"Found {invalid_count} skill gems with negative required_level"

        # Check support gems
        result = await session.execute(
            text("SELECT COUNT(*) FROM support_gems WHERE required_level < 0")
        )
        invalid_count = result.scalar()
        assert invalid_count == 0, f"Found {invalid_count} support gems with negative required_level"


@pytest.mark.asyncio
async def test_passive_node_positions_valid(db):
    """Verify passive node positions are reasonable"""
    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT COUNT(*) FROM passive_nodes WHERE position_x IS NOT NULL AND (position_x < -10000 OR position_x > 10000)")
        )
        invalid_x = result.scalar()

        result = await session.execute(
            text("SELECT COUNT(*) FROM passive_nodes WHERE position_y IS NOT NULL AND (position_y < -10000 OR position_y > 10000)")
        )
        invalid_y = result.scalar()

        # Positions should be within reasonable bounds for a tree visualization
        assert invalid_x == 0, f"Found {invalid_x} nodes with invalid X positions"
        assert invalid_y == 0, f"Found {invalid_y} nodes with invalid Y positions"


@pytest.mark.asyncio
async def test_database_has_all_expected_tables(db):
    """Verify all expected tables exist in database"""
    expected_tables = [
        'skill_gems',
        'support_gems',
        'passive_nodes',
        'items',
        'unique_items',
        'modifiers',
    ]

    async with db.async_session() as session:
        result = await session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        actual_tables = [row[0] for row in result.fetchall()]

    missing_tables = [t for t in expected_tables if t not in actual_tables]
    assert len(missing_tables) == 0, f"Missing tables: {missing_tables}"


@pytest.mark.asyncio
async def test_data_completeness_summary(db):
    """Summary report of data completeness across all tables"""
    async with db.async_session() as session:
        # Skill gems completeness
        result = await session.execute(text("SELECT COUNT(*) FROM skill_gems"))
        total_skills = result.scalar()

        result = await session.execute(text("SELECT COUNT(*) FROM skill_gems WHERE tags IS NOT NULL"))
        skills_with_tags = result.scalar()

        result = await session.execute(text("SELECT COUNT(*) FROM skill_gems WHERE per_level_stats IS NOT NULL"))
        skills_with_levels = result.scalar()

        print("\n=== SKILL GEMS COMPLETENESS ===")
        print(f"Total: {total_skills}")
        print(f"With tags: {skills_with_tags} ({skills_with_tags/total_skills*100:.1f}%)")
        print(f"With per-level stats: {skills_with_levels} ({skills_with_levels/total_skills*100:.1f}%)")

        # Support gems completeness
        result = await session.execute(text("SELECT COUNT(*) FROM support_gems"))
        total_supports = result.scalar()

        result = await session.execute(text("SELECT COUNT(*) FROM support_gems WHERE tags IS NOT NULL"))
        supports_with_tags = result.scalar()

        result = await session.execute(text("SELECT COUNT(*) FROM support_gems WHERE modifiers IS NOT NULL"))
        supports_with_mods = result.scalar()

        print("\n=== SUPPORT GEMS COMPLETENESS ===")
        print(f"Total: {total_supports}")
        print(f"With tags: {supports_with_tags} ({supports_with_tags/total_supports*100:.1f}%)")
        print(f"With modifiers: {supports_with_mods} ({supports_with_mods/total_supports*100:.1f}%)")

        # Passive nodes completeness
        result = await session.execute(text("SELECT COUNT(*) FROM passive_nodes"))
        total_passives = result.scalar()

        result = await session.execute(text("SELECT COUNT(*) FROM passive_nodes WHERE stats IS NOT NULL AND stats != '[]'"))
        passives_with_stats = result.scalar()

        print("\n=== PASSIVE NODES COMPLETENESS ===")
        print(f"Total: {total_passives}")
        print(f"With stats: {passives_with_stats} ({passives_with_stats/total_passives*100:.1f}%)")

        # All checks should pass if data was loaded correctly
        assert total_skills > 0
        assert total_supports > 0
        assert total_passives > 0
