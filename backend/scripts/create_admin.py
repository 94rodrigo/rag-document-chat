"""
Create or update an admin user with enterprise plan and full access.

Usage:
    python scripts/create_admin.py
    python scripts/create_admin.py --email admin@example.com --name "Admin" --password "MyPass1"
"""
from __future__ import annotations

import argparse
import asyncio
import sys


def _hash(password: str) -> str:
    """Hash password using bcrypt directly (avoids passlib/bcrypt version conflicts)."""
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


async def main(email: str, name: str, password: str) -> None:
    from sqlalchemy import update
    from sqlalchemy.ext.asyncio import async_sessionmaker

    # Import all models so SQLAlchemy can resolve cross-model relationships
    import app.domain.auth.models           # noqa: F401
    import app.domain.billing.models        # noqa: F401
    import app.domain.conversations.models  # noqa: F401
    import app.domain.documents.models      # noqa: F401

    from app.domain.auth.models import Plan, User
    from app.domain.auth.repository import UserRepository
    from app.infrastructure.database import enable_pgvector, engine

    await enable_pgvector()

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    hashed_pw = _hash(password)

    async with session_factory() as session:
        repo = UserRepository(session)
        existing = await repo.get_by_email(email)

        if existing:
            await session.execute(
                update(User)
                .where(User.email == email)
                .values(
                    plan=Plan.enterprise,
                    is_active=True,
                    is_verified=True,
                    hashed_password=hashed_pw,
                    name=name,
                )
            )
            await session.commit()
            print(f"[updated] {email}  →  plan=enterprise, active, verified")
        else:
            user = await repo.create(
                name=name,
                email=email.lower(),
                hashed_password=hashed_pw,
                plan=Plan.enterprise,
            )
            await session.execute(
                update(User)
                .where(User.id == user.id)
                .values(is_active=True, is_verified=True)
            )
            await session.commit()
            print(f"[created] {email}  |  id={user.id}")

    print()
    print("Admin user")
    print("─────────────────────────────────────────────────")
    print(f"  Email      {email}")
    print(f"  Name       {name}")
    print(f"  Plan       enterprise")
    print(f"  Documents  unlimited")
    print(f"  Queries    unlimited / month")
    print(f"  Storage    unlimited")
    print(f"  Rate limit 1 000 req / minute")
    print(f"  Active     yes")
    print(f"  Verified   yes")
    print()
    print("Login:")
    print(f'  POST /api/v1/auth/login')
    print(f'  {{"email": "{email}", "password": "<password>"}}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create Citenest admin user")
    parser.add_argument("--email",    default="admin@citenest.com")
    parser.add_argument("--name",     default="Admin")
    parser.add_argument("--password", default=None)
    args = parser.parse_args()

    if args.password is None:
        import getpass
        args.password = getpass.getpass("Password: ")

    p = args.password
    if len(p) < 8 or not any(c.isupper() for c in p) or not any(c.isdigit() for c in p):
        print("Password must be ≥8 chars with at least one uppercase letter and one digit.")
        sys.exit(1)

    asyncio.run(main(args.email, args.name, args.password))
