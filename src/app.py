import streamlit as st
import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai.types import GenerateContentConfig
from src.mock_client import MockClient
from src.wrapper import LimitedClient
from src.parser import extract_json, sanitize_evaluation
from src.prompts import system_prompt


# Load environment variables
load_dotenv()

st.set_page_config(page_title="LLM Judge - AI vs Human", layout="wide")

st.title("⚖️ LLM Judge: AI vs Human")

# Initialize session state
if "api_key" not in st.session_state:
    st.session_state.api_key = None

if "evaluation_result" not in st.session_state:
    st.session_state.evaluation_result = None

if "truncation_warning" not in st.session_state:
    st.session_state.truncation_warning = False

# 1. Startup Screen
if st.session_state.api_key is None:
    st.caption("Enter your Gemini API Key to access the evaluation dashboard")
    
    key_input = st.text_input("Gemini API Key", type="password", placeholder="Enter your key here...")
    
    if st.button("Enter Judge", disabled=not key_input):
        os.environ["GEMINI_API_KEY"] = key_input
        st.session_state.api_key = key_input
        
        # Initialize client with the provided key
        # base_client = MockClient(api_key=key_input) # Mock for local development
        base_client = genai.Client(api_key=key_input)
        st.session_state.client = LimitedClient(base_client, tier="free")
        st.rerun()

# 2. Main Evaluation Screen
else:
    st.caption("Evaluate content authenticity using multimodal analysis")

    # Sidebar for configuration and navigation
    st.sidebar.header("Configuration")
    
    # Tier Selection
    tier_options = {"Free Tier": "free", "Tier 1 Paid": "tier1"}
    selected_tier_label = st.sidebar.radio("Select Subscription Tier", list(tier_options.keys()), index=0)
    selected_tier = tier_options[selected_tier_label]
    
    # Update client tier
    if "client" in st.session_state:
        st.session_state.client.set_tier(selected_tier)

    st.sidebar.divider()
    
    st.sidebar.subheader("Model Selection")
    model_options = ["gemini-2.5-flash", "gemini-2.5-flash-lite"]
    selected_model = st.sidebar.selectbox("Select Model for Analysis", model_options)

    def run_evaluation(content, is_video=False):
        """Business logic for content evaluation."""
        try:
            with st.spinner("Analyzing content..."):
                if is_video:
                    uploaded_file = st.session_state.client.files.upload(file=content.name)
                    prompt = "Analyze this video and determine if it was created by an AI or a human. Return your response ONLY in the specified JSON format."
                    contents = [prompt, uploaded_file]
                else:
                    prompt = f"Analyze the following text and determine if it was written by an AI or a human. Return your response ONLY in the specified JSON format:\n\n{content}"
                    contents = prompt

                response = st.session_state.client.models.generate_content(
                    model=selected_model,
                    contents=contents,
                    config=GenerateContentConfig(system_instruction=system_prompt)
                )
                
                st.session_state.evaluation_result = {
                    "raw_text": response.text,
                    "metadata": response.usage_metadata,
                    "type": "Video" if is_video else "Text"
                }
        except Exception as e:
            st.error(f"Analysis failed: {str(e)}")

    # Tabs for different input types
    tab_text, tab_video = st.tabs(["📝 Text Evaluation", "🎬 Video Evaluation"])

    with tab_text:
        text_input = st.text_area(
            "Paste text to evaluate:", 
            height=200, 
            placeholder="Enter the content you want the judge to analyze..."
        )
        if st.button("Analyze Text", disabled=not text_input):
            st.session_state.truncation_warning = False
            words = text_input.split()
            if len(words) > 1000:
                text_input = " ".join(words[:1000])
                st.session_state.truncation_warning = True
            
            if st.session_state.truncation_warning:
                st.warning("⚠️ Input text exceeded 1000 words. It has been truncated for analysis.")
            run_evaluation(text_input, is_video=False)

    with tab_video:
        video_file = st.file_uploader(
            "Upload a video for evaluation:", 
            type=["mp4", "mpeg", "mov", "avi", "webm"],

        )
        if video_file:
            MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
            if video_file.size > MAX_FILE_SIZE:
                st.error(f"❌ Video file is too large ({video_file.size / (1024*1024):.1f} MB). Please upload a file smaller than 20 MB.")
            else:
                st.video(video_file)
                if st.button("Analyze Video"):
                    st.session_state.truncation_warning = False
                    run_evaluation(video_file, is_video=True)

    # Result Section
    if st.session_state.evaluation_result:
        if st.session_state.truncation_warning:
            st.warning("⚠️ Note: The input text was truncated to 1000 words for this analysis.")
        st.divider()
        res = st.session_state.evaluation_result
        raw_data = extract_json(res["raw_text"])
        structured_data = sanitize_evaluation(raw_data)

        if structured_data:
            st.subheader(f"Judge Verdict ({res['type']})")
            
            # 1. Origin Analysis
            origin = structured_data["origin_analysis"]
            col1, col2 = st.columns([1, 2])
            with col1:
                st.metric("Prediction", origin["prediction"])
                st.metric("Confidence", f"{float(origin['confidence_score'])*100:.1f}%")
            with col2:
                st.markdown(f"**Technical Reasoning:**\n{origin['technical_reasoning']}")
                if origin["text_artifacts"] != "[Missing]":
                    st.write("**Text Artifacts:**", ", ".join(origin["text_artifacts"]) if isinstance(origin["text_artifacts"], list) else origin["text_artifacts"])
                if origin["video_artifacts"] != "[Missing]":
                    st.write("**Video Artifacts:**", ", ".join(origin["video_artifacts"]) if isinstance(origin["video_artifacts"], list) else origin["video_artifacts"])

            st.divider()
            
            # 2. Social & Distribution
            col_soc, col_dist = st.columns(2)
            with col_soc:
                st.subheader("Social Performance")
                social = structured_data["social_performance"]
                st.write(f"**Virality Score:** {social['virality_score']}/10")
                st.write(f"**Drivers:** {', '.join(social['performance_drivers']) if isinstance(social['performance_drivers'], list) else social['performance_drivers']}")
                st.info(social["strategic_reasoning"])
                
            with col_dist:
                st.subheader("Distribution Strategy")
                dist = structured_data["distribution_strategy"]
                st.write(f"**Target Audiences:** {', '.join(dist['target_audiences']) if isinstance(dist['target_audiences'], list) else dist['target_audiences']}")
                st.write(f"**Resonance Factor:** {dist['resonance_factor']}")

            st.divider()
            
            # 3. Summary
            st.subheader("Analysis Summary")
            st.success(structured_data["metadata"]["analysis_summary"])

        else:
            # Fallback to raw text if parsing fails completely
            st.subheader("Raw Analysis Output")
            st.warning("Could not parse structured JSON from response. Showing raw output below:")
            st.code(res["raw_text"])
        
        # Metadata and Token Usage
        with st.expander("Technical Analysis Details"):
            cols = st.columns(3)
            metadata = res["metadata"]
            cols[0].metric("Prompt Tokens", metadata.prompt_token_count)
            cols[1].metric("Response Tokens", metadata.candidates_token_count)
            cols[2].metric("Total Tokens", metadata.total_token_count)
            st.write(f"**Model used:** {selected_model}")

    st.sidebar.divider()
    st.sidebar.subheader("App Controls")
    st.sidebar.info(f"Active Model: {selected_model}")

    if st.sidebar.button("Reset Evaluation"):
        st.session_state.evaluation_result = None
        st.session_state.truncation_warning = False
        st.rerun()

    if st.sidebar.button("Change API Key"):
        # Clear sensitive state and environment variable
        st.session_state.api_key = None
        st.session_state.client = None
        st.session_state.evaluation_result = None
        if "GEMINI_API_KEY" in os.environ:
            del os.environ["GEMINI_API_KEY"]
        st.rerun()
