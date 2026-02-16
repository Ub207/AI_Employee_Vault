"""Service for WhatsApp operations using Twilio."""

import logging
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

from backend.config import Settings

logger = logging.getLogger(__name__)


class WhatsappService:
    def __init__(self):
        self.settings = Settings()
        self.client = None
        if self.settings.TWILIO_ACCOUNT_SID and self.settings.TWILIO_AUTH_TOKEN:
            try:
                self.client = Client(self.settings.TWILIO_ACCOUNT_SID, self.settings.TWILIO_AUTH_TOKEN)
            except Exception as e:
                logger.error(f"Failed to initialize Twilio client: {e}")

    async def send_message(self, to: str, body: str) -> bool:
        """Send a WhatsApp message via Twilio."""
        if not self.client:
            logger.error("Twilio client not initialized.")
            return False

        try:
            # Twilio WhatsApp numbers must be prefixed with 'whatsapp:'
            from_number = f"whatsapp:{self.settings.TWILIO_PHONE_NUMBER}" if not self.settings.TWILIO_PHONE_NUMBER.startswith("whatsapp:") else self.settings.TWILIO_PHONE_NUMBER
            to_number = f"whatsapp:{to}" if not to.startswith("whatsapp:") else to

            message = self.client.messages.create(
                from_=from_number,
                body=body,
                to=to_number
            )
            logger.info(f"Sent WhatsApp message to {to}: {message.sid}")
            return True
        except TwilioRestException as e:
            logger.error(f"Twilio error sending to {to}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending WhatsApp to {to}: {e}")
            return False
