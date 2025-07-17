#!/usr/bin/env python3
"""
SMS testing script for Marty - Test real SMS sending and receiving.
This script helps test the full SMS pipeline including webhook handling.

FOR INTERNAL DEVELOPER TESTING ONLY - NOT FOR PRODUCTION USE
"""

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import colorama
from colorama import Fore, Style
from dotenv import load_dotenv

# Initialize colorama for cross-platform color support
colorama.init()

# Load environment variables from .env file
load_dotenv()

# Add the project root to the Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Create logs directory if it doesn't exist
(PROJECT_ROOT / "logs").mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(str(PROJECT_ROOT / "logs" / "sms_test.log")),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@dataclass
class SMSTestConfig:
    """Configuration for SMS testing."""

    # Required environment variables
    required_env_vars: list[str] = field(
        default_factory=lambda: [
            "SINCH_API_TOKEN",
            "SINCH_SERVICE_PLAN_ID",
            "ANTHROPIC_API_KEY",
        ]
    )

    # SMS configuration
    default_from_number: str = "+12345678901"  # Will be overridden by env var
    webhook_url: str = "https://your-domain.com/webhook/sms"  # Update this

    # Test configuration
    max_test_messages: int = 10
    message_delay: float = 2.0  # seconds between messages

    commands: dict[str, str] = field(
        default_factory=lambda: {
            "quit": "Exit the SMS test",
            "exit": "Exit the SMS test",
            "send": "Send a test SMS",
            "webhook": "Test webhook payload processing",
            "config": "Show current configuration",
            "help": "Show available commands",
            "history": "Show message history",
            "clear": "Clear message history",
        }
    )


class SMSTestError(Exception):
    """Base exception for SMS test errors."""

    pass


class ConfigurationError(SMSTestError):
    """Raised when configuration is invalid."""

    pass


class SMSTest:
    """SMS testing interface for Marty."""

    def __init__(self, config: SMSTestConfig | None = None):
        self.config = config or SMSTestConfig()
        self.message_history: list[dict[str, Any]] = []
        self.sinch_client = None

    def _print_banner(self) -> None:
        """Print the SMS test banner."""
        banner = f"""
{Fore.CYAN}📱 Marty SMS Test Interface{Style.RESET_ALL}
{Fore.CYAN}{"=" * 50}{Style.RESET_ALL}
{Fore.YELLOW}Commands:{Style.RESET_ALL}
"""
        for cmd, desc in self.config.commands.items():
            banner += f"  {Fore.GREEN}{cmd}{Style.RESET_ALL}: {desc}\n"
        banner += f"{Fore.CYAN}{'=' * 50}{Style.RESET_ALL}"
        print(banner)

    def _print_config(self) -> None:
        """Print current configuration."""
        print(f"\n{Fore.BLUE}⚙️  Current Configuration:{Style.RESET_ALL}")
        print(
            f"  {Fore.CYAN}Sinch Service Plan ID:{Style.RESET_ALL} {os.getenv('SINCH_SERVICE_PLAN_ID', 'Not set')}"
        )
        print(
            f"  {Fore.CYAN}Sinch API Token:{Style.RESET_ALL} {'Set' if os.getenv('SINCH_API_TOKEN') else 'Not set'}"
        )
        print(
            f"  {Fore.CYAN}From Number:{Style.RESET_ALL} {self.config.default_from_number}"
        )
        print(f"  {Fore.CYAN}Webhook URL:{Style.RESET_ALL} {self.config.webhook_url}")
        print(
            f"  {Fore.CYAN}Max Test Messages:{Style.RESET_ALL} {self.config.max_test_messages}"
        )

        # Check if we have a virtual number assigned
        if not os.getenv("SINCH_FROM_NUMBER"):
            print(
                f"\n{Fore.YELLOW}⚠️  No SINCH_FROM_NUMBER set in .env{Style.RESET_ALL}"
            )
            print("   You need to get a virtual number from Sinch Dashboard")
            print("   Visit: https://dashboard.sinch.com/sms/api/rest")

    def _print_help(self) -> None:
        """Print help information."""
        print(f"\n{Fore.BLUE}📖 Available Commands:{Style.RESET_ALL}")
        for cmd, desc in self.config.commands.items():
            print(f"  {Fore.GREEN}{cmd}{Style.RESET_ALL}: {desc}")

        print(f"\n{Fore.BLUE}📋 Usage Examples:{Style.RESET_ALL}")
        print(
            f"  {Fore.GREEN}send{Style.RESET_ALL} - Send a test message to your phone"
        )
        print(
            f"  {Fore.GREEN}webhook{Style.RESET_ALL} - Simulate incoming webhook from your phone"
        )
        print(f"  {Fore.GREEN}config{Style.RESET_ALL} - Check your Sinch configuration")

        print(f"\n{Fore.BLUE}🔧 Setup Required:{Style.RESET_ALL}")
        print("  1. Get a virtual number from Sinch Dashboard")
        print("  2. Set SINCH_FROM_NUMBER in your .env file")
        print("  3. Use 'send' command to test SMS sending")

    def _print_history(self) -> None:
        """Print message history."""
        if not self.message_history:
            print(f"\n{Fore.YELLOW}📭 No messages in history{Style.RESET_ALL}")
            return

        print(f"\n{Fore.BLUE}📜 Message History:{Style.RESET_ALL}")
        for i, msg in enumerate(self.message_history, 1):
            direction = "📤" if msg["direction"] == "outbound" else "📥"
            timestamp = msg["timestamp"].strftime("%H:%M:%S")
            print(f"  {i}. {direction} {timestamp} {msg['from']} → {msg['to']}")
            print(f"     {msg['content']}")

    def _validate_environment(self) -> None:
        """Validate that all required environment variables are set."""
        missing_vars = []
        for var in self.config.required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        if missing_vars:
            raise ConfigurationError(
                f"❌ Missing required environment variables: {', '.join(missing_vars)}\n"
                f"Please set these in your .env file"
            )

    async def _initialize_sinch_client(self) -> None:
        """Initialize the Sinch client."""
        try:
            from src.tools.external.sinch import sinch_client

            self.sinch_client = sinch_client
            print(f"{Fore.GREEN}✅ Sinch client initialized{Style.RESET_ALL}")
        except Exception as e:
            raise SMSTestError(f"Failed to initialize Sinch client: {e}") from e

    async def _send_test_sms(self, to_phone: str, message: str) -> None:
        """Send a test SMS message."""
        try:
            print(f"\n{Fore.MAGENTA}📤 Sending SMS...{Style.RESET_ALL}")

            # Show normalized numbers for debugging
            from src.tools.external.sinch import normalize_phone_number

            normalized_to = normalize_phone_number(to_phone)
            normalized_from = normalize_phone_number(self.config.default_from_number)

            print(f"  {Fore.CYAN}Normalized To:{Style.RESET_ALL} {normalized_to}")
            print(f"  {Fore.CYAN}Normalized From:{Style.RESET_ALL} {normalized_from}")

            response = await self.sinch_client.send_sms(
                body=message,
                to=[to_phone],
                from_=self.config.default_from_number,
            )

            # Log the message
            self.message_history.append(
                {
                    "direction": "outbound",
                    "from": self.config.default_from_number,
                    "to": to_phone,
                    "content": message,
                    "timestamp": datetime.now(UTC),
                    "response": response,
                }
            )

            print(f"{Fore.GREEN}✅ SMS sent successfully!{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}To:{Style.RESET_ALL} {to_phone}")
            print(f"  {Fore.CYAN}Message:{Style.RESET_ALL} {message}")
            print(
                f"  {Fore.CYAN}Response ID:{Style.RESET_ALL} {response.get('id', 'N/A')}"
            )

        except Exception as e:
            logger.error(f"Failed to send SMS: {e}")
            print(f"{Fore.RED}❌ Failed to send SMS: {e}{Style.RESET_ALL}")

    async def _simulate_webhook(self, from_phone: str, message: str) -> None:
        """Simulate an incoming webhook and process it through Marty."""
        try:
            print(
                f"\n{Fore.MAGENTA}🔄 Processing incoming message through Marty...{Style.RESET_ALL}"
            )

            # Create webhook payload
            webhook_payload = {
                "id": f"test_{datetime.now(UTC).timestamp()}",
                "type": "mo_text",
                "from": {"type": "number", "endpoint": from_phone},
                "to": {"type": "number", "endpoint": self.config.default_from_number},
                "message": message,
                "received_at": datetime.now(UTC).isoformat(),
            }

            # Process through SMS handler
            from src.sms_handler import process_incoming_sms
            from src.tools.external.sinch import SinchSMSWebhookPayload

            payload = SinchSMSWebhookPayload.model_validate(webhook_payload)

            # Log incoming message
            self.message_history.append(
                {
                    "direction": "inbound",
                    "from": from_phone,
                    "to": self.config.default_from_number,
                    "content": message,
                    "timestamp": datetime.now(UTC),
                    "payload": webhook_payload,
                }
            )

            # Process the message (this will generate AI response and send SMS)
            await process_incoming_sms(payload)

            print(f"{Fore.GREEN}✅ Webhook processed successfully!{Style.RESET_ALL}")
            print(f"  {Fore.CYAN}From:{Style.RESET_ALL} {from_phone}")
            print(f"  {Fore.CYAN}Message:{Style.RESET_ALL} {message}")
            print(
                f"  {Fore.CYAN}AI Response:{Style.RESET_ALL} Should be sent to {from_phone}"
            )

        except Exception as e:
            logger.error(f"Failed to process webhook: {e}")
            print(f"{Fore.RED}❌ Failed to process webhook: {e}{Style.RESET_ALL}")

    def _handle_command(self, command: str) -> bool:
        """Handle special commands. Returns True if should exit."""
        command_lower = command.lower()

        if command_lower in ["quit", "exit"]:
            print(f"\n{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")
            return True

        if command_lower == "config":
            self._print_config()
            return False

        if command_lower == "help":
            self._print_help()
            return False

        if command_lower == "history":
            self._print_history()
            return False

        if command_lower == "clear":
            self.message_history = []
            print(f"\n{Fore.GREEN}🧹 Message history cleared!{Style.RESET_ALL}")
            return False

        return False

    async def _interactive_send(self) -> None:
        """Interactive SMS sending."""
        try:
            to_phone = input(
                f"\n{Fore.CYAN}📱 Enter recipient phone number (with country code): {Style.RESET_ALL}"
            ).strip()
            if not to_phone:
                print(f"{Fore.RED}❌ Phone number is required{Style.RESET_ALL}")
                return

            message = input(
                f"{Fore.CYAN}💬 Enter message to send: {Style.RESET_ALL}"
            ).strip()
            if not message:
                print(f"{Fore.RED}❌ Message is required{Style.RESET_ALL}")
                return

            await self._send_test_sms(to_phone, message)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⏹️  Send cancelled{Style.RESET_ALL}")

    async def _interactive_webhook(self) -> None:
        """Interactive webhook simulation."""
        try:
            from_phone = input(
                f"\n{Fore.CYAN}📱 Enter sender phone number (your phone): {Style.RESET_ALL}"
            ).strip()
            if not from_phone:
                print(f"{Fore.RED}❌ Phone number is required{Style.RESET_ALL}")
                return

            message = input(
                f"{Fore.CYAN}💬 Enter message from your phone: {Style.RESET_ALL}"
            ).strip()
            if not message:
                print(f"{Fore.RED}❌ Message is required{Style.RESET_ALL}")
                return

            await self._simulate_webhook(from_phone, message)

        except KeyboardInterrupt:
            print(f"\n{Fore.YELLOW}⏹️  Webhook simulation cancelled{Style.RESET_ALL}")

    async def start_test(self) -> None:
        """Start the interactive SMS test session."""
        try:
            self._print_banner()
            self._validate_environment()

            # Initialize Sinch client
            await self._initialize_sinch_client()

            # Set default from number from environment
            if os.getenv("SINCH_FROM_NUMBER"):
                self.config.default_from_number = os.getenv("SINCH_FROM_NUMBER")
            else:
                print(
                    f"\n{Fore.YELLOW}⚠️  Warning: SINCH_FROM_NUMBER not set in .env{Style.RESET_ALL}"
                )
                print(f"   Using default number: {self.config.default_from_number}")
                print("   You should get a virtual number from Sinch Dashboard")

            print(f"\n{Fore.GREEN}🚀 SMS Test Interface Ready!{Style.RESET_ALL}")
            print(
                f"{Fore.YELLOW}💡 Tip: Type 'help' for available commands{Style.RESET_ALL}"
            )

            # Main interaction loop
            while True:
                try:
                    user_input = input(
                        f"\n{Fore.GREEN}📱 SMS Test>{Style.RESET_ALL} "
                    ).strip()

                    if not user_input:
                        continue

                    # Handle commands
                    if self._handle_command(user_input):
                        break

                    # Handle specific actions
                    if user_input.lower() == "send":
                        await self._interactive_send()
                    elif user_input.lower() == "webhook":
                        await self._interactive_webhook()
                    else:
                        print(
                            f"{Fore.RED}❌ Unknown command: {user_input}{Style.RESET_ALL}"
                        )
                        print(
                            f"{Fore.YELLOW}💡 Type 'help' for available commands{Style.RESET_ALL}"
                        )

                except KeyboardInterrupt:
                    print(f"\n\n{Fore.YELLOW}👋 Goodbye!{Style.RESET_ALL}")
                    break
                except Exception as e:
                    logger.error(f"Error in test loop: {e}")
                    print(f"{Fore.RED}❌ Error: {e}{Style.RESET_ALL}")
                    print(
                        f"{Fore.YELLOW}💡 Try again or type 'quit' to exit{Style.RESET_ALL}"
                    )

        except ConfigurationError as e:
            print(f"\n{Fore.RED}{e}{Style.RESET_ALL}")
            return
        except Exception as e:
            logger.error(f"Failed to start SMS test: {e}")
            print(f"\n{Fore.RED}❌ Failed to start SMS test: {e}{Style.RESET_ALL}")
            return


async def main() -> None:
    """Main entry point."""
    try:
        config = SMSTestConfig()
        sms_test = SMSTest(config)
        await sms_test.start_test()
    except Exception as e:
        logger.error(f"Failed to run SMS test: {e}")
        print(f"{Fore.RED}❌ Failed to run SMS test: {e}{Style.RESET_ALL}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
