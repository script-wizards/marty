#!/usr/bin/env python3
"""
Test script to explore Hardcover API capabilities.

Usage:
1. Set your HARDCOVER_API_TOKEN environment variable:
   export HARDCOVER_API_TOKEN="Bearer your_token_here"

2. Install dependencies:
   pip install httpx gql aiohttp

3. Run the script:
   python explore_hardcover_api.py
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

from config import config


async def test_simple_request():
    """Test basic HTTP request to Hardcover API."""
    token = os.getenv("HARDCOVER_API_TOKEN")
    if not token:
        print("❌ Please set HARDCOVER_API_TOKEN environment variable")
        print("   Format: export HARDCOVER_API_TOKEN='Bearer your_token_here'")
        return

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Marty-SMS-Bot/1.0 (Book recommendation bot)",
    }

    # Simple test query to verify connection
    test_query = {
        "query": """
            query {
                me {
                    id
                    username
                }
            }
        """
    }

    async with httpx.AsyncClient() as client:
        try:
            print("🔍 Testing Hardcover API connection...")
            response = await client.post(
                config.HARDCOVER_API_URL,
                headers=headers,
                json=test_query,
                timeout=30.0,
            )

            print(f"📡 Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"✅ Connected successfully!")
                print(f"   User: {data.get('data', {}).get('me', {})}")
                return True
            else:
                print(f"❌ Failed: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error: {e}")
            return False


async def explore_schema():
    """Explore the Hardcover GraphQL schema."""
    token = os.getenv("HARDCOVER_API_TOKEN")
    if not token:
        return

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Marty-SMS-Bot/1.0 (Book recommendation bot)",
    }

    # GraphQL introspection query to understand available types and queries
    introspection_query = {
        "query": """
            query IntrospectionQuery {
                __schema {
                    queryType { 
                        name
                        fields {
                            name
                            description
                            type {
                                name
                                kind
                            }
                        }
                    }
                    types {
                        name
                        kind
                        description
                        fields {
                            name
                            description
                            type {
                                name
                                kind
                                ofType {
                                    name
                                    kind
                                }
                            }
                        }
                    }
                }
            }
        """
    }

    async with httpx.AsyncClient() as client:
        try:
            print("\n🔍 Exploring GraphQL schema...")
            response = await client.post(
                config.HARDCOVER_API_URL,
                headers=headers,
                json=introspection_query,
                timeout=30.0,
            )

            if response.status_code == 200:
                schema_data = response.json()
                schema = schema_data.get("data", {}).get("__schema", {})

                # Print available root queries
                query_type = schema.get("queryType", {})
                print(
                    f"\n📚 Available root queries in {query_type.get('name', 'Query')}:"
                )

                for field in query_type.get("fields", []):
                    name = field.get("name")
                    description = field.get("description", "No description")
                    type_info = field.get("type", {})
                    type_name = type_info.get("name") or type_info.get("kind")
                    print(f"  • {name}: {type_name}")
                    if description != "No description":
                        print(f"    └─ {description}")

                # Look for Book-related types
                print(f"\n📖 Book-related types:")
                types = schema.get("types", [])

                for type_def in types:
                    type_name = type_def.get("name", "")
                    if "book" in type_name.lower() or "author" in type_name.lower():
                        print(f"  • {type_name} ({type_def.get('kind')})")
                        if type_def.get("description"):
                            print(f"    └─ {type_def.get('description')}")

                        # Show fields for object types
                        if type_def.get("kind") == "OBJECT":
                            fields = type_def.get("fields", [])[
                                :5
                            ]  # Show first 5 fields
                            for field in fields:
                                field_name = field.get("name")
                                field_type = field.get("type", {})
                                print(
                                    f"      ◦ {field_name}: {field_type.get('name') or field_type.get('kind')}"
                                )

                # Save full schema for detailed analysis
                with open("hardcover_schema.json", "w") as f:
                    json.dump(schema_data, f, indent=2)
                print(f"\n💾 Full schema saved to 'hardcover_schema.json'")

                return True
            else:
                print(f"❌ Schema exploration failed: {response.text}")
                return False

        except Exception as e:
            print(f"❌ Error exploring schema: {e}")
            return False


async def test_book_search():
    """Test book search functionality."""
    token = os.getenv("HARDCOVER_API_TOKEN")
    if not token:
        return

    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Marty-SMS-Bot/1.0 (Book recommendation bot)",
    }

    # Try different possible book search queries using the correct schema
    search_queries = [
        # Try simple books query with proper syntax
        {
            "name": "Simple books query",
            "query": """
                query {
                    books(limit: 3) {
                        id
                        title
                        description
                    }
                }
            """,
        },
        # Try the search query with correct SearchOutput fields
        {
            "name": "General search",
            "query": """
                query {
                    search(query: "harry potter") {
                        error
                        ids
                        query
                        results
                    }
                }
            """,
        },
        # Try trending books with ALL required parameters (from, to, limit, offset)
        {
            "name": "Trending books",
            "query": """
                query {
                    books_trending(from: "2025-04-01", to: "2025-07-01", limit: 10, offset: 0) {
                        error
                        ids
                    }
                }
            """,
        },
        # Try books by primary key
        {
            "name": "Book by ID",
            "query": """
                query {
                    books_by_pk(id: 1) {
                        id
                        title
                        description
                    }
                }
            """,
        },
    ]

    async with httpx.AsyncClient() as client:
        print(f"\n🔍 Testing book search capabilities...")

        for search_test in search_queries:
            print(f"\n  Testing: {search_test['name']}")

            try:
                response = await client.post(
                    config.HARDCOVER_API_URL,
                    headers=headers,
                    json={"query": search_test["query"]},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    if "errors" in data:
                        print(f"    ❌ GraphQL errors: {data['errors']}")
                    else:
                        result_data = data.get("data", {})
                        print(f"    ✅ Success: {len(str(result_data))} chars of data")
                        print(f"    📖 Result keys: {list(result_data.keys())}")
                else:
                    print(
                        f"    ❌ HTTP {response.status_code}: {response.text[:100]}..."
                    )

            except Exception as e:
                print(f"    ❌ Error: {e}")


async def main():
    """Run all tests."""
    print("🚀 Hardcover API Explorer")
    print("=" * 50)

    # Test basic connection
    success = await test_simple_request()
    if not success:
        print("\n❌ Basic connection failed. Please check your token.")
        return

    # Explore schema
    await explore_schema()

    # Test book search
    await test_book_search()

    print("\n" + "=" * 50)
    print(
        "✅ Exploration complete! Check 'hardcover_schema.json' for full schema details."
    )


if __name__ == "__main__":
    asyncio.run(main())
