import razorpay

from app.core.config import settings


def get_razorpay_client() -> razorpay.Client:
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def create_razorpay_order(amount_paise: int, receipt: str) -> dict:
    client = get_razorpay_client()
    return client.orders.create({
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
        "payment_capture": 1,
    })


def verify_payment_signature(
    razorpay_order_id: str,
    razorpay_payment_id: str,
    razorpay_signature: str,
) -> bool:
    client = get_razorpay_client()
    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
        return True
    except Exception:
        return False


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    client = get_razorpay_client()
    try:
        client.utility.verify_webhook_signature(
            body.decode(), signature, settings.RAZORPAY_KEY_SECRET
        )
        return True
    except Exception:
        return False


def issue_refund(razorpay_payment_id: str, amount_paise: int) -> dict:
    client = get_razorpay_client()
    return client.payment.refund(razorpay_payment_id, {"amount": amount_paise})


# Backward-compatible class used by orders.py
class RazorpayService:
    def create_order(self, amount_paise: int) -> dict:
        import uuid as _uuid
        return create_razorpay_order(amount_paise, receipt=str(_uuid.uuid4()))


razorpay_service = RazorpayService()
