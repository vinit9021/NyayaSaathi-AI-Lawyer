"""Session-local text intake, bulk review, and editable neutral request drafts."""
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import streamlit as st

from nyayasaathi.config import ConfigurationError, Settings, load_streamlit_settings
from nyayasaathi.conversation import FIELDS, OPTIONAL_FIELDS, evidence_checklist, localize, unanswered_fields
from nyayasaathi.conversation import process_turn
from nyayasaathi.extraction import INTAKE_VERSION, confirm_facts
from nyayasaathi.llm.factory import create_llm_client
from nyayasaathi.models import CaseState
from nyayasaathi.retrieval import CatalogueError, load_catalogue, retrieve
from nyayasaathi.safety import ground_claims
from nyayasaathi.drafting import LABELS, NOTICE, create_draft, download_bytes, fingerprint, require_safe_case

ROOT = Path(__file__).resolve().parent
BUILD = sha256(b''.join(path.read_bytes() for path in
                       [ROOT / 'app.py', *sorted((ROOT / 'nyayasaathi').rglob('*.py'))])).hexdigest()[:10]


def reset_case(language):
    for key in list(st.session_state):
        if key.startswith(('fact_', 'draft_')) or key in {'case', 'live_consent'}:
            del st.session_state[key]
    st.session_state.case = CaseState(language=language)


def render_sources(state, catalogue):
    with st.expander('Legal information and sources / कानूनी जानकारी और स्रोत'):
        if state.blocked or not state.assessment or not state.assessment.allow_drafting:
            st.info('Legal options are unavailable until scope and safety checks pass.')
            return
        values = {f.name: f.value for f in state.facts}
        jurisdiction = values.get('state') if 'state' not in state.conflicts else None
        retrieved = retrieve(catalogue, topic=state.topic, state=jurisdiction,
                             text=' '.join(f.value or '' for f in state.facts + state.proposals))
        sources = tuple(m.source for m in retrieved.matches)
        claims = ground_claims(sources, state.assessment,
                               tuple(c.id for s in sources for c in s.claims if c.kind != 'statutory'),
                               state=jurisdiction, language=state.language)
        if retrieved.gaps or claims.gaps:
            st.warning('Legal position not verified. No statutory entitlement or deadline is established. / कानूनी अधिकार सत्यापित नहीं हैं।')
        for claim in claims.claims:
            st.markdown(claim.text)
            st.markdown(f'[{claim.title}]({claim.url})')
            st.caption(f'{claim.locator} • checked {claim.checked_on} • {claim.limitations}')


def render_review(state):
    with st.expander('Review all details / सभी जानकारी जाँचें', expanded=bool(state.proposals)):
        st.caption('Edit together, then confirm once. Confirmation records your statements, not proof. Dates: YYYY-MM-DD; INR amounts: digits without commas.')
        revision = fingerprint(state)[:16]
        current = {f.name: f for f in state.facts + state.proposals}
        with st.form('fact_review'):
            columns = st.columns(2)
            inputs = {}
            for index, name in enumerate(FIELDS[state.topic] + OPTIONAL_FIELDS[state.topic]):
                fact = current.get(name)
                key = f'fact_{state.case_id}_{revision}_{name}'
                with columns[index % 2]:
                    if name in state.conflicts:
                        previous = next((f.value for f in state.facts if f.name == name), None)
                        st.caption('Previously confirmed / पिछली पुष्टि: ' + (previous or 'Unknown / अज्ञात'))
                    entered = st.text_area(LABELS[name], value=(fact.value or '') if fact else '',
                                           key=key, max_chars=500, height=68)
                    unknown = st.checkbox('Unknown / अज्ञात — ' + LABELS[name],
                                          value=bool(fact and fact.value is None), key=key + '_unknown')
                    if unknown or entered.strip():
                        inputs[name] = None if unknown else entered.strip()
            submitted = st.form_submit_button('Confirm entered details / दर्ज जानकारी की पुष्टि', disabled=state.blocked is not None)
        if submitted:
            try:
                st.session_state.case = confirm_facts(state, inputs)
                st.rerun()
            except ValueError as error:
                st.warning(str(error))


def render_draft(state):
    st.subheader('Document draft / दस्तावेज़ मसौदा')
    st.caption('Template-based, not advocate-approved. Only confirmed statements are used. Nothing is sent or filed. / केवल पुष्टि की गई जानकारी से मसौदा; कुछ भेजा नहीं जाएगा।')
    try:
        require_safe_case(state)
    except ValueError as error:
        st.info(str(error))
        return
    if st.button('Generate / regenerate draft / मसौदा बनाएँ', key='draft_generate'):
        st.session_state.draft_document = create_draft(state)
        st.session_state.draft_text = st.session_state.draft_document.text
    draft = st.session_state.get('draft_document')
    if draft is None:
        st.caption('Confirm details above first. Missing or unconfirmed values become visible placeholders. Regenerate explicitly to replace an existing draft.')
        return
    if draft.critical_missing:
        st.warning('Please provide or review: ' + '; '.join(LABELS[n] for n in draft.critical_missing))
    if draft.missing:
        st.caption('Placeholders remain: ' + '; '.join(LABELS[n] for n in draft.missing))
    st.caption('Draft body is in English; your confirmed statements keep their original language. Edits do not change case facts.')
    edited = st.text_area('Edit draft / मसौदा संपादित करें', key='draft_text', height=340, max_chars=12000)
    with st.expander('Preview / पूर्वावलोकन'):
        st.text(NOTICE + '\n\n' + edited)
    revision = sha256((draft.fingerprint + edited).encode()).hexdigest()[:16]
    reviewed = st.checkbox('I reviewed the text and placeholders and take responsibility for its use / मैंने मसौदा जाँच लिया है', key='draft_review_' + revision)
    payload = b''
    error = None
    try:
        payload = download_bytes(state, draft, edited, reviewed=reviewed)
    except ValueError as exc:
        error = str(exc)
    if error:
        st.caption(error)
    st.download_button('Download text / टेक्स्ट डाउनलोड', data=payload, file_name=draft.filename,
                       mime='text/plain; charset=utf-8', disabled=error is not None, key='draft_download')


def main():
    st.set_page_config(page_title='NyayaSaathi', page_icon='⚖️')
    st.title('NyayaSaathi')
    st.caption('Application build: ' + BUILD + ' • Intake contract: ' + INTAKE_VERSION)
    if st.session_state.get('app_build', BUILD) != BUILD:
        st.warning('Application updated. Your session facts remain; review them or start a New case before retesting.')
    st.session_state.app_build = BUILD
    preference = st.selectbox('Response language / जवाब की भाषा', ['English', 'हिन्दी'], key='language')
    language = 'hi' if preference == 'हिन्दी' else 'en'
    st.caption(localize('AI legal-information assistant, not a licensed lawyer. Information may be incomplete or outdated. Review drafts and consult a qualified lawyer for advice or urgent matters.',
                        'AI कानूनी-जानकारी सहायक, लाइसेंस प्राप्त वकील नहीं। जानकारी अधूरी या पुरानी हो सकती है। मसौदा जाँचें और सलाह या तात्कालिक मामलों में योग्य वकील से मिलें।', language))
    st.caption('Online shopping complaints and rental deposits only. Fictional examples only; no private case data. / केवल काल्पनिक खरीदारी और जमा राशि के मामले।')
    mode = st.selectbox('Mode / तरीका', ['Choose mode', 'Offline simulation', 'Gemini'], key='mode')
    if st.session_state.get('active_mode') != mode:
        reset_case(language)
        st.session_state.active_mode = mode
    if 'case' not in st.session_state:
        st.session_state.case = CaseState(language=language)
    if st.button('New case / नया मामला', type='primary'):
        reset_case(language)
        st.rerun()
    state = replace(st.session_state.case, language=language)
    st.session_state.case = state
    if mode == 'Choose mode':
        st.info('Choose a mode to begin. Voice input is not available yet.')
        return
    client = None
    if mode == 'Offline simulation':
        st.warning('OFFLINE SIMULATION / ऑफलाइन अनुकरण — deterministic rules, not live AI. No API requests. Limited language understanding.')
        client = create_llm_client(Settings(llm_provider='simulation'))
    else:
        st.info('Gemini sends submitted text and case context to Google. Session-only app storage; provider policies still apply.')
        consent = st.checkbox('I permit live Gemini requests using fictional data / काल्पनिक डेटा से Gemini अनुरोध की अनुमति', key='live_consent')
        try:
            settings = load_streamlit_settings(dotenv_path=ROOT / '.env')
            settings.require_gemini()
            if settings.llm_provider != 'gemini':
                raise ConfigurationError('Gemini mode requires LLM_PROVIDER=gemini.')
            if consent:
                client = create_llm_client(settings, allow_live=True)
        except ConfigurationError as error:
            st.warning(str(error) + ' Offline simulation can be selected explicitly; no fallback occurs.')
    try:
        catalogue = load_catalogue()
    except CatalogueError:
        catalogue = ()
        st.warning('Sources unavailable. Legal claims disabled; neutral requests do not establish rights.')
    for message in state.history:
        with st.chat_message(message.role):
            st.text(message.content)
    if state.blocked:
        st.error('This case needs qualified legal help. Start a new case only for a separate supported issue.')
    if state.last_result and getattr(state.last_result, 'issues', ()):
        with st.expander('Intake checks / जानकारी की जाँच'):
            st.caption('Unverified fields were omitted. No raw conversation or model output is logged.')
            st.table([{'Field': issue.field or 'Unknown field', 'Check': issue.code}
                      for issue in state.last_result.issues])
    if state.topic in FIELDS:
        st.subheader('Case summary / मामले का सार')
        st.caption('Your assertions, not independently proven facts. / आपके कथन, स्वतंत्र रूप से सिद्ध तथ्य नहीं।')
        current = {f.name: f for f in state.facts + state.proposals}
        if current:
            with st.container(border=True):
                st.table([{'Detail / जानकारी': LABELS[f.name],
                           'Value / मान': (f.value[:150] + '…' if len(f.value or '') > 150 else f.value) or 'Unknown / अज्ञात',
                           'Status / स्थिति': 'Conflict / विरोध' if f.name in state.conflicts else 'Confirmed / पुष्टि' if f.confirmed else 'Review / जाँचें'}
                          for f in list(current.values())[:6]])
                st.caption('Full details and corrections are in the review form below. / पूरी जानकारी नीचे जाँचें।')
        absent = unanswered_fields(state)
        st.caption(('Missing / अज्ञात: ' + '; '.join(LABELS[n] for n in absent)) if absent else 'All essential details provided; review any unconfirmed values.')
        if state.proposals:
            st.caption('Awaiting confirmation / पुष्टि बाकी: ' + '; '.join(LABELS[f.name] for f in state.proposals))
        if state.conflicts:
            st.warning('Conflicting details: prior confirmed values remain until you review and correct them.')
        render_review(state)
        st.caption('Evidence to gather / सबूत सूची: ' + ' • '.join(evidence_checklist(state.topic, language)))
        render_sources(state, catalogue)
        render_draft(state)
    submitted = st.chat_input('Describe your issue / अपनी समस्या बताएँ', max_chars=4000,
                              disabled=client is None or state.blocked is not None or len(state.processed_ids) >= 20)
    if submitted and client:
        with st.spinner('Checking your message / संदेश की जाँच…'):
            st.session_state.case = process_turn(state, submitted, uuid4().hex, client, catalogue)
        st.rerun()
    st.caption('Session-only memory; refresh may lose your case. Maximum 20 submissions. New case clears facts and drafts.')


if __name__ == '__main__':
    main()
