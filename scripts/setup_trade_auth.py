#!/usr/bin/env python3
"""
Trade Site Authentication Helper

Opens a browser window, lets the user log into pathofexile.com,
then automatically extracts and saves the POESESSID cookie.

No more manual cookie hunting in DevTools!

Usage:
    python scripts/setup_trade_auth.py

Requirements:
    pip install playwright
    playwright install chromium
"""

import asyncio
import sys
import os
from pathlib import Path

try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("ERROR: Playwright not installed!")
    print("\nInstall with:")
    print("  pip install playwright")
    print("  playwright install chromium")
    sys.exit(1)


class TradeAuthHelper:
    """Helper to authenticate with PoE trade site and extract session cookie"""

    def __init__(self):
        self.base_dir = Path(__file__).parent.parent
        self.env_file = self.base_dir / ".env"
        self.session_cookie = None

    async def run(self):
        """Main authentication flow"""
        print("=" * 80)
        print("Path of Exile Trade Site Authentication Helper")
        print("=" * 80)
        print()
        print("This tool will:")
        print("  1. Open a browser to pathofexile.com")
        print("  2. Let you log in with your account")
        print("  3. Automatically extract your session cookie")
        print("  4. Save it to your .env file")
        print()
        print("You'll need your PoE account credentials.")
        print()

        input("Press Enter to open the browser and begin authentication...")
        print()

        async with async_playwright() as p:
            # Launch browser in headed mode (user can see it)
            print("Opening browser...")
            browser = await p.chromium.launch(
                headless=False,
                args=['--start-maximized']
            )

            # Create context with viewport
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )

            page = await context.new_page()

            try:
                # Navigate to PoE trade site
                print("Navigating to pathofexile.com...")
                await page.goto("https://www.pathofexile.com/trade2/search/poe2/Standard")

                print()
                print("=" * 80)
                print("PLEASE LOG IN TO YOUR PATH OF EXILE ACCOUNT")
                print("=" * 80)
                print()
                print("Steps:")
                print("  1. Click 'Log In' button in the top right")
                print("  2. Enter your account credentials")
                print("  3. Complete any 2FA if required")
                print("  4. Wait for the page to load after login")
                print()
                print("This script will automatically detect when you're logged in")
                print("and extract your session cookie.")
                print()
                print("Waiting for you to log in...")

                # Wait for user to log in by checking for the cookie
                # The POESESSID cookie appears after successful login
                max_wait = 300  # 5 minutes
                check_interval = 2  # Check every 2 seconds

                for i in range(0, max_wait, check_interval):
                    await asyncio.sleep(check_interval)

                    # Get all cookies
                    cookies = await context.cookies()

                    # Look for POESESSID
                    poesessid = None
                    for cookie in cookies:
                        if cookie['name'] == 'POESESSID':
                            poesessid = cookie['value']
                            break

                    if poesessid:
                        self.session_cookie = poesessid
                        print()
                        print("=" * 80)
                        print("SUCCESS! Session cookie detected!")
                        print("=" * 80)
                        print()
                        print(f"Cookie value (first 20 chars): {poesessid[:20]}...")
                        print(f"Cookie length: {len(poesessid)} characters")
                        print()
                        break

                    # Show progress
                    if i % 10 == 0 and i > 0:
                        print(f"  Still waiting... ({i}s elapsed)")

                if not self.session_cookie:
                    print()
                    print("ERROR: Timeout waiting for login (5 minutes elapsed)")
                    print("Please try again and complete login faster.")
                    await browser.close()
                    return False

                # Give user a moment to see the success message
                await asyncio.sleep(2)

                # Close browser
                print("Closing browser...")
                await browser.close()

                # Save to .env
                success = self._save_to_env()

                if success:
                    print()
                    print("=" * 80)
                    print("AUTHENTICATION COMPLETE!")
                    print("=" * 80)
                    print()
                    print("Your trade API is now configured!")
                    print()
                    print("Next steps:")
                    print("  1. Restart your MCP server")
                    print("  2. Try using the search_trade_items tool")
                    print("  3. Search for items to upgrade your build!")
                    print()
                    return True
                else:
                    return False

            except Exception as e:
                print()
                print(f"ERROR: {e}")
                import traceback
                traceback.print_exc()
                await browser.close()
                return False

    def _save_to_env(self) -> bool:
        """Save POESESSID to .env file"""
        if not self.session_cookie:
            print("ERROR: No session cookie to save")
            return False

        print()
        print("Saving to .env file...")

        # Read existing .env if it exists
        env_lines = []
        poesessid_found = False

        if self.env_file.exists():
            with open(self.env_file, 'r', encoding='utf-8') as f:
                env_lines = f.readlines()

            # Update existing POESESSID line
            for i, line in enumerate(env_lines):
                if line.strip().startswith('POESESSID='):
                    env_lines[i] = f'POESESSID={self.session_cookie}\n'
                    poesessid_found = True
                    break

        # Add new POESESSID line if not found
        if not poesessid_found:
            if env_lines and not env_lines[-1].endswith('\n'):
                env_lines.append('\n')
            env_lines.append(f'\n# Path of Exile Trade Site Session Cookie\n')
            env_lines.append(f'# Obtained: {self._get_timestamp()}\n')
            env_lines.append(f'POESESSID={self.session_cookie}\n')

        # Write back to .env
        try:
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.writelines(env_lines)

            print(f"  Saved to: {self.env_file}")
            print("  Variable: POESESSID")
            print()
            print("IMPORTANT: This cookie will expire when you:")
            print("  - Log out of pathofexile.com")
            print("  - Clear your browser cookies")
            print("  - After ~30 days of inactivity")
            print()
            print("If trade searches stop working, run this script again!")
            print()

            return True

        except Exception as e:
            print(f"ERROR writing to .env: {e}")
            print()
            print("Manual fallback:")
            print(f"  Add this line to your .env file:")
            print(f"  POESESSID={self.session_cookie}")
            print()
            return False

    def _get_timestamp(self):
        """Get current timestamp for logging"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


async def main():
    """Entry point"""
    helper = TradeAuthHelper()

    try:
        success = await helper.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print()
        print()
        print("Authentication cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print()
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if sys.platform == 'win32':
        # Windows-specific: Set up event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(main())
