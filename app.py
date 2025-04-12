import streamlit as st
import PyPDF2
from docx import Document
import json
from google import genai
from dotenv import load_dotenv
import os
import re
import pandas as pd

# Load API Key from .env or environment variable (for Hugging Face Spaces)
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("❌ Gemini API key not found. Please set GEMINI_API_KEY.")
    st.stop()

# Utility: Extract text from PDF
def extract_text_from_pdf(file):
    reader = PyPDF2.PdfReader(file)
    text = ""
    for page in reader.pages:
        content = page.extract_text()
        if content:
            text += content + "\n"
    return text.strip()

# Utility: Extract text from DOCX
def extract_text_from_docx(file):
    doc = Document(file)
    return "\n".join([para.text for para in doc.paragraphs]).strip()

# Parse Gemini JSON response
def safe_parse_json(response_text):
    try:
        clean_text = re.sub(r"^```(?:json)?|```$", "", response_text.strip(), flags=re.MULTILINE)
        return json.loads(clean_text)
    except Exception as e:
        st.error("⚠️ Could not parse Gemini response as JSON. Showing raw response.")
        return {
            "summary": response_text,
            "highlights": None,
            "glossary": None
        }

# Call Gemini API
def call_gemini_api(document_text):
    client = genai.Client(api_key=api_key)

    prompt = (
        f"Analyze the following legal document:\n\n{document_text}\n\n"
        "Instructions:\n"
        "- Summarize the key points of the document.\n"
        "- Highlight obligations, rights, and critical clauses (as a list of objects with 'clause' and 'description').\n"
        "- Provide simplified explanations of complex legal terms (as a dictionary).\n"
        "Return the result as JSON with keys: 'summary', 'highlights', 'glossary'."
    )

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt
    )

    return safe_parse_json(response.text)

# Render Highlights as Table
def render_highlights(highlights):
    if isinstance(highlights, list) and all(isinstance(item, dict) for item in highlights):
        df = pd.DataFrame(highlights)
        st.table(df)
    elif isinstance(highlights, str):
        st.markdown(highlights)
    else:
        st.info("No highlights available.")

# Render Glossary as Table
def render_glossary(glossary):
    if isinstance(glossary, dict):
        glossary_list = [{"Term": term, "Explanation": explanation} for term, explanation in glossary.items()]
        df = pd.DataFrame(glossary_list)
        st.table(df)
    elif isinstance(glossary, str):
        st.markdown(glossary)
    else:
        st.info("No glossary available.")

# Main App
def main():
    st.set_page_config(page_title="Legal Document Summarizer", layout="wide")
    st.title("📄 Legal Document Summarizer")
    st.caption("Upload a legal document (PDF or DOCX) to get a summary, key highlights, and glossary of legal terms.")

    uploaded_file = st.file_uploader("Upload your document", type=["pdf", "docx"])

    if uploaded_file:
        if uploaded_file.type == "application/pdf":
            document_text = extract_text_from_pdf(uploaded_file)
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            document_text = extract_text_from_docx(uploaded_file)
        else:
            st.error("Unsupported file format.")
            return

        if not document_text.strip():
            st.error("No text extracted from the document.")
            return

        st.subheader("📄 Document Preview")
        st.text_area("Extracted Text", document_text, height=300)

        if st.button("Summarize Document"):
            with st.spinner("Calling Gemini..."):
                result = call_gemini_api(document_text)

                st.subheader("📝 Summary")
                st.write(result.get("summary", "No summary found."))

                st.subheader("📌 Highlights")
                render_highlights(result.get("highlights"))

                st.subheader("📘 Glossary")
                render_glossary(result.get("glossary"))

if __name__ == "__main__":
    main()
