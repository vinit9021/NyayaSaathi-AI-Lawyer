"""Text intake UI explicitly requested in milestone 3. No audio or drafting."""

from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from uuid import uuid4
import streamlit as st

from nyayasaathi.config import ConfigurationError, Settings, load_streamlit_settings
from nyayasaathi.conversation import FIELDS, evidence_checklist, localize, missing_fields, process_turn
from nyayasaathi.extraction import confirm_fact
from nyayasaathi.llm.factory import create_llm_client
from nyayasaathi.models import CaseState
from nyayasaathi.retrieval import CatalogueError, load_catalogue

ROOT = Path(__file__).resolve().parent
LABELS = {
    "problem": "Problem / समस्या", "seller": "Seller / विक्रेता", "city": "City / शहर",
    "state": "State / राज्य", "amount_paid": "Amount paid / भुगतान", "refund_amount": "Refund sought / माँगा गया रिफंड",
    "purchase_date": "Purchase date / खरीद की तारीख", "delivery_date": "Delivery date / डिलीवरी तारीख",
    "evidence": "Evidence described / बताए गए सबूत", "contact_attempts": "Contact history / संपर्क का विवरण",
    "desired_outcome": "Desired outcome / अपेक्षित समाधान", "deposit_paid": "Deposit paid / जमा राशि",
    "deposit_returned": "Deposit returned / लौटी जमा राशि", "move_out_date": "Move-out date / मकान छोड़ने की तारीख",
    "deductions": "Deductions / कटौतियाँ", "agreement": "Agreement terms / समझौते की शर्तें",
}


def reset_case(language: str) -> None:
    for key in list(st.session_state):
        if key.startswith("fact_") or key in {"case", "live_consent"}:
            del st.session_state[key]
    st.session_state.case = CaseState(language=language)


def main() -> None:
    st.set_page_config(page_title="NyayaSaathi", page_icon="⚖️")
    st.title("NyayaSaathi")
    preference = st.selectbox("Response language / जवाब की भाषा", ["English", "हिन्दी"], key="language")
    language = "hi" if preference == "हिन्दी" else "en"
    st.caption(localize(
        "AI legal-information assistant, not a licensed lawyer. Information may be incomplete or outdated. Consult a qualified lawyer for advice or urgent matters.",
        "यह AI कानूनी-जानकारी सहायक है, लाइसेंस प्राप्त वकील नहीं। जानकारी अधूरी या पुरानी हो सकती है। सलाह या तात्कालिक मामलों के लिए योग्य वकील से मिलें।", language))
    st.caption(localize("For online shopping complaints and rental deposits only. Synthetic examples only; do not enter real private case details.",
                        "केवल ऑनलाइन खरीद और किराये की जमा राशि के मामले। काल्पनिक उदाहरण ही दें; वास्तविक निजी जानकारी न दें।", language))
    mode = st.selectbox("Mode / तरीका", ["Choose mode", "Offline simulation", "Gemini"], key="mode")
    if st.session_state.get("active_mode") != mode:
        reset_case(language)
        st.session_state.active_mode = mode
    if "case" not in st.session_state:
        st.session_state.case = CaseState(language=language)
    if st.button("New case / नया मामला"):
        reset_case(language)
        st.rerun()
    state = replace(st.session_state.case, language=language)
    st.session_state.case = state
    if mode == "Choose mode":
        st.info("Choose a mode to begin. Voice and document drafting are not available yet.")
        return
    client = None
    if mode == "Offline simulation":
        st.warning("OFFLINE SIMULATION / ऑफलाइन अनुकरण — deterministic rules, not live AI. No API requests. Limited language understanding.")
        client = create_llm_client(Settings(llm_provider="simulation"))
    else:
        st.info(localize("Gemini mode sends your submitted text and case context to Google. This app stores them only in this session; provider policies still apply.",
                         "Gemini मोड में आपका भेजा पाठ और मामले का संदर्भ Google को जाएगा। ऐप इसे केवल इस सत्र में रखता है; प्रदाता की नीतियाँ अलग लागू हैं।", language))
        consent = st.checkbox("I permit live Gemini requests using fictional data / काल्पनिक डेटा से Gemini अनुरोध की अनुमति", key="live_consent")
        try:
            settings = load_streamlit_settings(dotenv_path=ROOT / ".env")
            settings.require_gemini()
            if settings.llm_provider != "gemini":
                raise ConfigurationError("Gemini mode requires LLM_PROVIDER=gemini.")
            if consent:
                client = create_llm_client(settings, allow_live=True)
        except ConfigurationError as error:
            st.warning(str(error) + " Offline simulation can be selected explicitly; no fallback occurs.")
    try:
        catalogue = load_catalogue()
    except CatalogueError:
        catalogue = ()
        st.warning(localize("Sources could not be loaded. Legal claims are disabled; only intake is available.",
                            "स्रोत नहीं खुले। कानूनी दावे बंद हैं; केवल जानकारी इकट्ठी की जा सकती है।", language))
    for message in state.history:
        with st.chat_message(message.role):
            if message.role == "user":
                st.text(message.content)  # User assertions cannot inject Markdown links/HTML.
            else:
                st.markdown(message.content)
    if state.blocked:
        st.error(localize("This case needs qualified legal help. Start a new case only for a separate supported issue.",
                          "इस मामले में योग्य कानूनी मदद चाहिए। नया मामला केवल अलग समर्थित समस्या के लिए शुरू करें।", language))
    if state.last_result and state.last_result.error:
        st.error(state.last_result.message)
    if state.last_result and state.last_result.gaps:
        st.warning(localize("Source limitations remain; no statutory entitlement or deadline has been verified for this case.",
                            "स्रोत सीमित हैं; इस मामले के अधिकार या कानूनी समय-सीमा सत्यापित नहीं हैं।", language))
    if state.topic in FIELDS:
        st.subheader(localize("Case summary — your statements, not proven facts", "मामले का सार — आपके कथन, सिद्ध तथ्य नहीं", language))
        rows = [{"Detail / जानकारी": LABELS[f.name], "Value / मान": f.value if f.value is not None else "Unknown / अज्ञात",
                 "Status / स्थिति": "User confirmed / पुष्टि" if f.confirmed else "Proposed — review / प्रस्तावित",
                 "Turn / संदेश": f.turn} for f in state.facts + state.proposals]
        if rows:
            st.table(rows)
        missing = missing_fields(state)
        st.caption(localize("Missing or not confirmed: ", "अज्ञात या अपुष्ट: ", language) + "; ".join(LABELS[f] for f in missing))
        if state.conflicts:
            st.warning(localize("Conflicting details — prior confirmed values are kept until you correct them: ",
                                "विरोधी जानकारी — आपके सुधार तक पुरानी पुष्टि सुरक्षित है: ", language) + "; ".join(LABELS[f] for f in state.conflicts))
        if not state.blocked:
            st.subheader(localize("Evidence checklist — gather if available", "सबूत सूची — उपलब्ध हों तो रखें", language))
            for item in evidence_checklist(state.topic, language):
                st.text("• " + item)
        with st.expander("Review, confirm or correct details / जानकारी जाँचें और सुधारें"):
            name = st.selectbox("Detail / जानकारी", FIELDS[state.topic], format_func=lambda f: LABELS[f], key="fact_field")
            current = next((f for f in state.proposals + state.facts if f.name == name), None)
            revision = sha256(repr((current.value, current.confirmed) if current else None).encode()).hexdigest()[:16]
            suffix = f"{state.case_id}_{name}_{len(state.processed_ids)}_{revision}"
            value = st.text_area("Your statement / आपका कथन", value=current.value or "" if current else "", key="fact_value_" + suffix, max_chars=500)
            unknown = st.checkbox("I do not know / मुझे नहीं पता", key="fact_unknown_" + suffix)
            st.caption("Dates: YYYY-MM-DD. INR amounts: digits without commas. Confirmation records your statement, not proof.")
            if st.button("Confirm detail / पुष्टि करें", disabled=state.blocked is not None):
                try:
                    st.session_state.case = confirm_fact(state, name, None if unknown else value.strip())
                    st.rerun()
                except ValueError as error:
                    st.warning(str(error))
    submitted = st.chat_input("Describe your issue / अपनी समस्या बताएँ", max_chars=4000,
                              disabled=client is None or state.blocked is not None or len(state.processed_ids) >= 20)
    if submitted and client is not None:
        with st.spinner(localize("Checking your message…", "आपका संदेश जाँचा जा रहा है…", language)):
            st.session_state.case = process_turn(state, submitted, uuid4().hex, client, catalogue)
        st.rerun()
    st.caption(localize("Session-only memory. Refresh may lose your case. Maximum 20 submissions; start a new case to reset.",
                        "जानकारी केवल सत्र में रहती है। रीफ्रेश से मिट सकती है। अधिकतम 20 संदेश; नए मामले से रीसेट करें।", language))


if __name__ == "__main__":
    main()
