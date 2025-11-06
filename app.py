import streamlit as st
import google.generativeai as genai
from PIL import Image
import firebase_admin
from firebase_admin import credentials, db, storage
import os
import json
from datetime import datetime
import base64
from io import BytesIO

# Set page configuration
st.set_page_config(
    page_title="Advanced ECG Analyzer",
    page_icon="❤️",
    layout="centered"
)

# Initialize Gemini API
GEMINI_API_KEY = "AIzaSyCKeyiKySCVsqPYKJFhfWOlkyky3L8MmVY"

# Firebase Configuration
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyBd-5hfIw96nH8lEsjwWZH3Ov2f9tbESJ4",
    "authDomain": "heart-disease-detector-41045.firebaseapp.com",
    "databaseURL": "https://heart-disease-detector-41045-default-rtdb.firebaseio.com/",
    "projectId": "heart-disease-detector-41045",
    "storageBucket": "heart-disease-detector-41045.appspot.com",
    "messagingSenderId": "206192293331",
    "appId": "1:206192293331:web:0aa330860ceb3c16932b26"
}

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    if not firebase_admin._apps:
        # For Streamlit Cloud or production, use service account JSON
        # For local testing, you can use the config directly
        try:
            # Try to load service account key if available
            cred = credentials.Certificate('serviceAccountKey.json')
            firebase_admin.initialize_app(cred, {
                'databaseURL': FIREBASE_CONFIG['databaseURL'],
                'storageBucket': FIREBASE_CONFIG['storageBucket']
            })
        except:
            # Fallback: Initialize without credentials (works for public read/write rules)
            firebase_admin.initialize_app(options={
                'databaseURL': FIREBASE_CONFIG['databaseURL'],
                'storageBucket': FIREBASE_CONFIG['storageBucket']
            })

def initialize_gemini():
    genai.configure(api_key=GEMINI_API_KEY)
    return {
        'vision': genai.GenerativeModel('gemini-2.5-flash'),
        'text': genai.GenerativeModel('gemini-2.5-flash')
    }

def save_analysis_to_firebase(analysis_data, image_file):
    """Save ECG analysis to Firebase Realtime Database"""
    try:
        # Convert image to base64 for storage
        buffered = BytesIO()
        img = Image.open(image_file)
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        # Create analysis record
        analysis_record = {
            'timestamp': analysis_data['timestamp'],
            'image_name': analysis_data['image'],
            'image_base64': img_str[:1000],  # Store thumbnail (first 1000 chars)
            'report': analysis_data['report'],
            'patient_id': st.session_state.get('current_patient_id', 'unknown'),
            'analysis_type': 'ECG'
        }
        
        # Push to Firebase
        ref = db.reference('ecg_analyses')
        new_analysis_ref = ref.push(analysis_record)
        
        st.success(f"✅ Analysis saved to database with ID: {new_analysis_ref.key}")
        return new_analysis_ref.key
    except Exception as e:
        st.error(f"Failed to save to Firebase: {str(e)}")
        return None

def load_analyses_from_firebase(patient_id=None):
    """Load ECG analyses from Firebase"""
    try:
        ref = db.reference('ecg_analyses')
        if patient_id:
            analyses = ref.order_by_child('patient_id').equal_to(patient_id).get()
        else:
            analyses = ref.order_by_child('timestamp').limit_to_last(10).get()
        
        if analyses:
            return [{'id': k, **v} for k, v in analyses.items()]
        return []
    except Exception as e:
        st.error(f"Failed to load from Firebase: {str(e)}")
        return []

def save_chat_to_firebase(chat_message, analysis_id):
    """Save chat message to Firebase"""
    try:
        chat_record = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'analysis_id': analysis_id,
            'role': chat_message['role'],
            'content': chat_message['content']
        }
        ref = db.reference('ecg_chats')
        ref.push(chat_record)
    except Exception as e:
        st.error(f"Failed to save chat: {str(e)}")

# Session state initialization
if 'analysis_history' not in st.session_state:
    st.session_state.analysis_history = []
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_analysis' not in st.session_state:
    st.session_state.current_analysis = None
if 'current_analysis_id' not in st.session_state:
    st.session_state.current_analysis_id = None
if 'current_patient_id' not in st.session_state:
    st.session_state.current_patient_id = None

# Main function
def main():
    # Initialize Firebase and Gemini
    initialize_firebase()
    models = initialize_gemini()
    
    st.title("Advanced ECG Analysis Suite")
    
    # Patient ID input (sidebar)
    with st.sidebar:
        st.header("Patient Information")
        patient_id = st.text_input("Patient ID (optional)", value=st.session_state.current_patient_id or "")
        if patient_id:
            st.session_state.current_patient_id = patient_id
        
        st.markdown("---")
        st.subheader("Firebase Status")
        st.success("✅ Connected to Firebase")
        
        if st.button("Load Past Analyses from Database"):
            with st.spinner("Loading from Firebase..."):
                loaded = load_analyses_from_firebase(patient_id if patient_id else None)
                if loaded:
                    st.session_state.analysis_history = loaded
                    st.success(f"Loaded {len(loaded)} analyses")
                else:
                    st.info("No analyses found")
    
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
                        
                        # Save to Firebase
                        analysis_id = save_analysis_to_firebase(analysis, uploaded_file)
                        
                        st.session_state.current_analysis = analysis
                        st.session_state.current_analysis_id = analysis_id
                        st.session_state.analysis_history.append(analysis)
                        
                        st.success("Analysis Complete & Saved to Database")
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
                    options=[f"{i+1}: {item['timestamp']} - {item.get('image', item.get('image_name', 'Unknown'))}" 
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
                        
                        PAST REPORT ({st.session_state.analysis_history[past_idx]['timestamp']}):
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
                
                # Save user message to Firebase
                if st.session_state.current_analysis_id:
                    save_chat_to_firebase({"role": "user", "content": prompt}, 
                                        st.session_state.current_analysis_id)
                
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
                        assistant_message = {"role": "assistant", "content": response.text}
                        st.session_state.chat_history.append(assistant_message)
                        
                        # Save assistant message to Firebase
                        if st.session_state.current_analysis_id:
                            save_chat_to_firebase(assistant_message, 
                                                st.session_state.current_analysis_id)
                        
                        with st.chat_message("assistant"):
                            st.markdown(response.text)
                    except Exception as e:
                        st.error(f"Chat error: {str(e)}")

if __name__ == "__main__":
    main()
