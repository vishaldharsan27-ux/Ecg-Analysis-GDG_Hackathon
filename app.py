import streamlit as st
import google.generativeai as genai
from PIL import Image
import os
import json
from datetime import datetime

# Set page configuration
st.set_page_config(
    page_title="Advanced ECG Analyzer",
    page_icon="❤️",
    layout="centered"
)

# Initialize Gemini API
GEMINI_API_KEY = "AIzaSyCKeyiKySCVsqPYKJFhfWOlkyky3L8MmVY"

def initialize_gemini():
    genai.configure(api_key=GEMINI_API_KEY)
    return {
        'vision': genai.GenerativeModel('gemini-2.5-flash'),
        'text': genai.GenerativeModel('gemini-2.5-flash')
    }

# Session state initialization
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None

# Main function
def main():
    models = initialize_gemini()
    
    st.title("Advanced ECG Analysis Suite")
    
    # Tab layout
    tab1, tab2, tab3 = st.tabs(["ECG Analysis", "Trend Analysis", "ECG Chatbot"])
    
    with tab1:
        st.header("ECG Report Analysis")
        st.markdown("""
        <style>
        .report-analysis { font-size: 16px; line-height: 1.6; }
        .disclaimer {
            font-size: 14px; color: #666;
            border-left: 3px solid #ff4b4b;
            padding-left: 10px; margin-top: 20px;
        }
        </style>
        <div class="report-analysis">
        Upload an ECG report image for detailed AI analysis:
        <ul>
            <li>Rhythm interpretation</li>
            <li>Potential abnormalities</li>
            <li>Clinical insights</li>
            <li>Recommended actions</li>
        </ul>
        </div>
        <div class="disclaimer">
        <strong>Important:</strong> This tool provides preliminary analysis only.
        </div>
        """, unsafe_allow_html=True)
        
        uploaded_file = st.file_uploader(
            "Choose an ECG report image (JPEG/PNG)",
            type=["jpg", "jpeg", "png"],
            key="ecg_upload"
        )
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded ECG Report", width=350)
            
            if st.button("Analyze ECG Report", key="analyze_btn"):
                with st.spinner("Performing comprehensive analysis..."):
                    try:
                        prompt = """As a senior cardiologist, analyze this ECG report with:
                        1. Basic Parameters (HR, rhythm, intervals)
                        2. Rhythm Analysis
                        3. Axis Determination
                        4. Waveform Abnormalities
                        5. Clinical Interpretation
                        6. Recommendations
                        
                        Use medical terminology with only main points"""
                        
                        response = models['vision'].generate_content([prompt, image])
                        analysis = {
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'image': uploaded_file.name,
                            'report': response.text
                        }
                        st.session_state.current_analysis = analysis
                        st.session_state.analysis_history.append(analysis)
                        
                        st.success("Analysis Complete")
                        st.markdown("---")
                        st.subheader("ECG Analysis Report")
                        st.markdown(response.text)
                        st.markdown("---")
                        
                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")

    with tab2:
        st.header("Trend Analysis: Compare Past & Present ECGs")
        
        if len(st.session_state.analysis_history) < 1:
            st.warning("No previous analyses found. Please analyze at least 2 ECGs first.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Select Past Analysis")
                past_selection = st.selectbox(
                    "Choose previous report:",
                    options=[f"{i+1}: {item['timestamp']} - {item['image']}" 
                            for i, item in enumerate(st.session_state.analysis_history)],
                    key="past_select"
                )
                past_idx = int(past_selection.split(":")[0]) - 1
                st.markdown(st.session_state.analysis_history[past_idx]['report'])
            
            with col2:
                st.subheader("Current Analysis")
                if st.session_state.current_analysis:
                    st.markdown(st.session_state.current_analysis['report'])
                else:
                    st.warning("No current analysis available")
            
            if st.button("Compare Trends", key="compare_btn") and st.session_state.current_analysis:
                with st.spinner("Identifying trends and changes..."):
                    try:
                        past_report = st.session_state.analysis_history[past_idx]['report']
                        current_report = st.session_state.current_analysis['report']
                        
                        comparison_prompt = f"""Compare these two ECG reports and identify clinically significant changes:
                        
                        PAST REPORT ({(st.session_state.analysis_history[past_idx]['timestamp'])}):
                        {past_report}
                        
                        CURRENT REPORT:
                        {current_report}
                        
                        Provide:
                        1. Summary of key changes
                        2. Clinical significance
                        3. Urgency level
                        4. Recommended follow-up actions
                        """
                        
                        comparison = models['text'].generate_content(comparison_prompt)
                        st.subheader("Trend Analysis Report")
                        st.markdown(comparison.text)
                    except Exception as e:
                        st.error(f"Comparison failed: {str(e)}")

    with tab3:
        st.header("ECG Analysis Chatbot")
        st.markdown("Ask follow-up questions about your ECG reports")
        
        if not st.session_state.current_analysis:
            st.warning("Please analyze an ECG report first before chatting")
        else:
            for message in st.session_state.chat_history:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
            
            if prompt := st.chat_input("Ask about your ECG..."):
                st.session_state.chat_history.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)
                
                context = f"""
                Current ECG Analysis:
                {st.session_state.current_analysis['report']}
                
                Chat History:
                {[msg['content'] for msg in st.session_state.chat_history]}
                """
                
                full_prompt = f"""As a cardiology assistant, answer this ECG-related question:
                Question: {prompt}
                
                Context:
                {context}
                
                Guidelines:
                - Be professional but approachable
                - Explain medical terms simply
                - If unsure, recommend consulting a cardiologist
                - Never provide definitive diagnoses
                """
                
                with st.spinner("Generating response..."):
                    try:
                        response = models['text'].generate_content(full_prompt)
                        st.session_state.chat_history.append({"role": "assistant", "content": response.text})
                        with st.chat_message("assistant"):
                            st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Chat error: {str(e)}")

if __name__ == "__main__":

    main()





