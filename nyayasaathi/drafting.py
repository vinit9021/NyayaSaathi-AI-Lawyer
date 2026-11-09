"""Neutral, deterministic requests. No model call, filing, or legal entitlement."""

from dataclasses import dataclass
from hashlib import sha256
import json
import re

from nyayasaathi.models import CaseState
from nyayasaathi.extraction import validate_confirmed_value
from nyayasaathi.safety import assess_request, require_drafting_allowed

NOTICE = ('DRAFT — review before use / मसौदा — उपयोग से पहले जाँचें\n'
          'User statements, not independently verified facts. Not prepared or approved by a licensed advocate.\n'
          'User edits are unverified. Review all details and placeholders. Nothing has been sent or filed.')
LABELS = {
    'sender_name': 'Your name / आपका नाम', 'sender_contact': 'Your contact / आपका संपर्क',
    'recipient_contact': 'Recipient contact/address / प्राप्तकर्ता का संपर्क',
    'seller': 'Seller/platform / विक्रेता', 'product': 'Product / सामान',
    'order_reference': 'Order reference / ऑर्डर संख्या', 'purchase_date': 'Purchase date / खरीद तारीख',
    'delivery_date': 'Delivery date / डिलीवरी तारीख', 'amount_paid': 'Amount paid (INR) / भुगतान',
    'refund_amount': 'Requested refund (INR) / माँगा रिफंड', 'problem': 'Your account of the problem / समस्या का विवरण',
    'contact_attempts': 'Previous communications / पिछली बातचीत', 'evidence': 'Evidence described / बताए सबूत',
    'desired_outcome': 'Requested resolution / अपेक्षित समाधान', 'state': 'State / राज्य', 'city': 'City / शहर',
    'landlord': 'Landlord name / मकान मालिक', 'rental_property': 'Rental property / किराये का पता',
    'deposit_paid': 'Deposit paid (INR) / जमा राशि', 'deposit_returned': 'Deposit already returned (INR) / लौटी राशि',
    'agreement': 'Agreement terms as reported / बताए समझौते के नियम', 'agreement_date': 'Agreement date / समझौता तारीख',
    'move_out_date': 'Move-out/key handover date / मकान छोड़ने की तारीख', 'deductions': 'Disputed deductions / विवादित कटौती',
}
FIELDS = {
    'consumer': ('sender_name', 'sender_contact', 'seller', 'recipient_contact', 'product', 'order_reference',
                 'purchase_date', 'delivery_date', 'amount_paid', 'refund_amount', 'city', 'state', 'problem',
                 'contact_attempts', 'evidence', 'desired_outcome'),
    'rental_deposit': ('sender_name', 'sender_contact', 'landlord', 'recipient_contact', 'rental_property',
                       'city', 'state', 'deposit_paid', 'deposit_returned', 'agreement', 'agreement_date',
                       'move_out_date', 'problem', 'deductions', 'contact_attempts', 'evidence', 'desired_outcome'),
}
CRITICAL = {'consumer': ('problem', 'amount_paid', 'desired_outcome'),
            'rental_deposit': ('problem', 'state', 'deposit_paid', 'desired_outcome')}
LEGAL = re.compile(r'https?://|www\.|\b(?:section|article|act)\s+\d|\b(?:statutory|judgment|guarantee(?:d|s)?|penalty|lawsuit|legally|entitled)\b|'
                   r'\blaw\s+(?:requires|says|provides)\b|'
                   r'\b\d+\s*(?:days?|hours?)\b|\b(?:v\.|vs\.)\s|धारा\s*\d|कानूनी धमकी|गारंटी|\d+\s*दिन', re.I)


@dataclass(frozen=True)
class Draft:
    text: str
    filename: str
    fingerprint: str
    missing: tuple[str, ...]
    critical_missing: tuple[str, ...]


def fingerprint(state: CaseState) -> str:
    data = (state.case_id, state.topic, state.language, state.processed_ids,
            [(f.name, f.value) for f in state.facts], [(f.name, f.value) for f in state.proposals], state.conflicts)
    return sha256(json.dumps(data, ensure_ascii=False).encode()).hexdigest()


def check_text(text: str) -> None:
    """Conservative screening, not a certification of arbitrary edited prose."""
    if not isinstance(text, str) or not text.strip() or len(text) > 12000:
        raise ValueError('Enter a draft between 1 and 12000 characters.')
    # Check each bounded line; reject oversized lines instead of dropping text.
    for line in text.splitlines():
        if line.strip():
            decision = assess_request(line)
            if decision.disposition in {'escalate', 'reject'} or 'invalid_or_oversized_input' in decision.reasons:
                raise ValueError('This text needs qualified legal review; unsafe or unsupported content cannot be exported.')
    if LEGAL.search(text):
        raise ValueError('Remove legal claims, citations, guarantees or fixed deadlines. This tool creates neutral requests only.')


def require_safe_case(state: CaseState) -> None:
    if state.blocked or state.assessment is None or state.assessment.topic != state.topic:
        raise ValueError('Complete supported-case scope and safety checks before drafting.')
    require_drafting_allowed(state.assessment)
    if state.conflicts:
        raise ValueError('Resolve conflicting details in the review form before drafting.')
    for message in state.history:
        if message.role == 'user':
            decision = assess_request(message.content)
            if decision.disposition in {'escalate', 'reject'}:
                raise ValueError('This case needs qualified legal help; drafting is blocked.')
    for fact in state.facts + state.proposals:
        if fact.value:
            check_text(fact.value)


def create_draft(state: CaseState) -> Draft:
    require_safe_case(state)
    values = {f.name: f.value for f in state.facts}
    for name, value in values.items():
        validate_confirmed_value(name, value)
    missing = tuple(name for name in FIELDS[state.topic] if not values.get(name))
    def value(name):
        return values.get(name) or '[Please provide: ' + LABELS[name] + ']'
    consumer = state.topic == 'consumer'
    subject = 'Consumer complaint / refund request' if consumer else 'Rental security deposit repayment request'
    recipient = 'seller' if consumer else 'landlord'
    lines = [f'Subject: {subject}', f'To: {value(recipient)}', value('recipient_contact'),
             f'From: {value("sender_name")}', value('sender_contact'), '', 'Dear Sir/Madam,', '',
             'I am writing to request a resolution based on my account below. These are my statements and the evidence I describe.']
    skip = {'sender_name', 'sender_contact', 'recipient_contact', recipient}
    lines.extend(f'{LABELS[name]}: {value(name)}' for name in FIELDS[state.topic] if name not in skip)
    lines += ['', ('Please consider my requested refund/resolution and provide a written response.' if consumer else
                   'Please return the deposit amount I have requested, or provide a written explanation and an itemized account of any deductions.'),
              'Please let me know what further information you need.', '', 'Yours sincerely,', value('sender_name')]
    if not consumer:
        lines += ['', 'This request does not assert any state-specific entitlement or determine whether deductions are lawful.']
    text = '\n'.join(lines)
    check_text(text)
    return Draft(text, 'consumer-request.txt' if consumer else 'deposit-request.txt', fingerprint(state), missing,
                 tuple(name for name in CRITICAL[state.topic] if name in missing))


def download_bytes(state: CaseState, draft: Draft, edited_text: str, *, reviewed: bool) -> bytes:
    require_safe_case(state)
    if draft.fingerprint != fingerprint(state):
        raise ValueError('Case details changed. Regenerate the draft and review it again before downloading.')
    if not reviewed:
        raise ValueError('Review the draft and acknowledge responsibility before downloading.')
    check_text(edited_text)
    return (NOTICE + '\n\n' + edited_text).encode('utf-8')
