"""Foundation entry point only; the conversational UI belongs to milestone 4."""

import streamlit as st


def main() -> None:
    st.title("NyayaSaathi")
    st.info("Foundation only. Chat, legal guidance, and voice are not available yet.")
    st.caption("AI legal-information assistant, not a licensed lawyer.")


if __name__ == "__main__":
    main()
