import argparse
import asyncio
import sys
from typing import Callable, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import AsyncSessionLocal
from app.account.repository import AccountRepository
from app.logging_config import get_logger

logger = get_logger("cli.admin")

async def promote_account(
    username: str,
    assume_yes: bool = False,
    session: Optional[AsyncSession] = None,
    input_func: Callable[[str], str] = input
) -> Tuple[bool, str]:
    """
    Promote an existing player account to administrator.

    Invariants:
    1. Requires an existing account (never creates an account).
    2. Never touches or resets passwords.
    3. Refuses empty, missing, or banned accounts.
    4. Requires explicit operator confirmation unless assume_yes=True.
    5. Idempotent: safe to run repeatedly.
    6. Does not modify any other account or database records.
    """
    clean_username = username.strip() if username else ""
    if not clean_username:
        msg = "Error: Username cannot be empty."
        logger.warning(msg)
        return False, msg

    async def _execute(db_session: AsyncSession) -> Tuple[bool, str]:
        repo = AccountRepository(db_session)
        account = await repo.get_by_username(clean_username, load_character=False)

        if not account:
            msg = f"Error: Account '{clean_username}' does not exist. Only existing accounts can be promoted."
            logger.warning(msg)
            return False, msg

        if account.is_banned:
            msg = f"Error: Account '{clean_username}' is banned. Cannot promote a banned account."
            logger.warning(msg)
            return False, msg

        if account.role == "admin":
            msg = f"Account '{clean_username}' (ID: {account.id}) is already an administrator. No changes applied."
            logger.info(msg)
            return True, msg

        # Require explicit interactive confirmation
        if not assume_yes:
            prompt_msg = (
                f"\n[SECURITY CONFIRMATION]\n"
                f"You are about to promote account '{account.username}' (ID: {account.id}) to ADMINISTRATOR.\n"
                f"Administrators possess full control over player accounts and moderation systems.\n"
                f"Are you sure you want to proceed? [y/N]: "
            )
            try:
                confirmation = input_func(prompt_msg).strip().lower()
            except (EOFError, KeyboardInterrupt):
                msg = "Operation aborted by user."
                logger.info(msg)
                return False, msg

            if confirmation not in ("y", "yes"):
                msg = "Promotion cancelled by operator."
                logger.info(msg)
                return False, msg

        # Apply promotion
        updated = await repo.update_role(account.id, "admin")
        msg = f"Success: Account '{updated.username}' (ID: {updated.id}) has been promoted to administrator."
        logger.info(f"AUDIT: Operator promoted account '{updated.username}' (ID: {updated.id}) to role 'admin'.")
        return True, msg

    if session is not None:
        return await _execute(session)
    else:
        async with AsyncSessionLocal() as new_session:
            return await _execute(new_session)

def main():
    parser = argparse.ArgumentParser(
        prog="python -m app.cli.admin",
        description="ROS Sothat Private Server - Local Administrative CLI"
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    promote_parser = subparsers.add_parser(
        "promote",
        help="Promote an existing player account to administrator"
    )
    promote_parser.add_argument(
        "username",
        type=str,
        help="Username of the existing player account to promote"
    )
    promote_parser.add_argument(
        "-y", "--yes",
        action="store_true",
        help="Skip interactive confirmation (for non-interactive scripts)"
    )

    args = parser.parse_args()

    if args.subcommand == "promote":
        success, message = asyncio.run(
            promote_account(args.username, assume_yes=args.yes)
        )
        print(message)
        sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
