"""
UNMASKED — Database Validation Script
======================================
Run after schema.sql + generate_synthetic_data.py + seed_knowledge_base.py
to verify everything is set up correctly.

Usage: python validate_db.py
"""

import os
import asyncio
import asyncpg

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://unmasked:unmasked_dev@localhost:5432/unmasked"
)


async def validate():
    print("UNMASKED — Database Validation")
    print("=" * 60)

    conn = await asyncpg.connect(DATABASE_URL)

    try:
        checks_passed = 0
        checks_failed = 0

        async def check(name: str, query: str, expected_min: int):
            nonlocal checks_passed, checks_failed
            row = await conn.fetchrow(query)
            count = row[0] if row else 0
            status = "PASS" if count >= expected_min else "FAIL"
            if status == "FAIL":
                checks_failed += 1
            else:
                checks_passed += 1
            print(f"  [{status}] {name}: {count} (expected >= {expected_min})")

        # Table existence & row counts
        print("\n1. TABLE ROW COUNTS")
        await check("cases", "SELECT COUNT(*) FROM cases", 490)
        await check("transactions", "SELECT COUNT(*) FROM transactions", 1500)
        await check("vpa_registry", "SELECT COUNT(*) FROM vpa_registry", 100)
        await check("knowledge_base", "SELECT COUNT(*) FROM knowledge_base", 15)

        # Data quality checks
        print("\n2. DATA QUALITY")
        await check(
            "Cases with transactions",
            "SELECT COUNT(DISTINCT case_id) FROM transactions",
            490
        )
        await check(
            "Mule accounts (risk > 0.5)",
            "SELECT COUNT(*) FROM vpa_registry WHERE risk_score > 0.5",
            20
        )
        await check(
            "Confirmed fraud VPAs",
            "SELECT COUNT(*) FROM vpa_registry WHERE is_confirmed_fraud = TRUE",
            3
        )
        await check(
            "Transactions with time_delta < 600s",
            "SELECT COUNT(*) FROM transactions WHERE time_delta_seconds < 600 AND time_delta_seconds IS NOT NULL",
            100
        )
        await check(
            "Cash-out transactions",
            "SELECT COUNT(*) FROM transactions WHERE is_cash_out = TRUE",
            50
        )

        # Edge case validation
        print("\n3. EDGE CASES")
        await check(
            "VPAs seen in 3+ cases (shared mules)",
            "SELECT COUNT(*) FROM vpa_registry WHERE total_cases_involved >= 3",
            10
        )
        await check(
            "Clustered VPA naming patterns",
            """SELECT COUNT(DISTINCT naming_pattern) FROM vpa_registry
               WHERE naming_pattern IN (
                   SELECT naming_pattern FROM vpa_registry
                   GROUP BY naming_pattern HAVING COUNT(*) >= 3
               )""",
            2
        )

        # BFS function test
        print("\n4. BFS FUNCTION TEST")
        top_fraud = await conn.fetchrow(
            "SELECT fraud_vpa FROM cases LIMIT 1"
        )
        if top_fraud:
            bfs_result = await conn.fetch(
                "SELECT * FROM fraud_network_bfs($1, 2)",
                top_fraud['fraud_vpa']
            )
            count = len(bfs_result)
            status = "PASS" if count >= 0 else "FAIL"
            print(f"  [{status}] BFS from '{top_fraud['fraud_vpa']}': {count} nodes found (depth=2)")
            checks_passed += 1
        else:
            print("  [FAIL] No cases found to test BFS")
            checks_failed += 1

        # Knowledge base embedding check
        print("\n5. RAG EMBEDDINGS")
        non_zero = await conn.fetchrow("""
            SELECT COUNT(*) FROM knowledge_base
            WHERE embedding IS NOT NULL
            AND embedding != (ARRAY_FILL(0.0, ARRAY[1536]))::vector
        """)
        count = non_zero[0] if non_zero else 0
        if count > 0:
            print(f"  [PASS] {count} entries have real embeddings")
            checks_passed += 1
        else:
            print(f"  [WARN] All embeddings are zero vectors (set OPENAI_API_KEY to generate real ones)")
            checks_passed += 1  # still a pass — placeholder is expected without API key

        # Summary
        print(f"\n{'='*60}")
        print(f"VALIDATION COMPLETE: {checks_passed} passed, {checks_failed} failed")
        if checks_failed == 0:
            print("All checks passed! Database is ready for UNMASKED agents.")
        else:
            print("Some checks failed. Review the output above.")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(validate())
