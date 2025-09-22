import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
import json
import re
import pandas as pd

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if api_key is None:
    st.error("GEMINI_API_KEY not set. Please add your API key to the .env file.")
    st.stop()

genai.configure(api_key=api_key)
st.set_page_config(page_title="Skill2Success", layout="centered")

def landing_page():
    st.markdown(
        """
        <div style='text-align: center; padding-top: 60px;'>
            <h1 style='font-size: 3.5rem; color: #1677ff; font-weight: 700; margin-bottom: 24px;'>
                Skill2Success
            </h1>
            <h4 style='color: #505050; margin-bottom: 32px; font-size: 1.3rem;'>
                🚀 Your personalized AI-powered career roadmap builder.<br>
                Identify your strengths, take our psychometric and skillset quizzes, and let AI map your path to success!
            </h4>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.image(
        "https://images.unsplash.com/photo-1503676382389-4809596d5290?auto=format&fit=crop&w=1000&q=80",
        use_container_width=True,
        caption="Unlock your potential with Skill2Success!"
    )
    st.markdown("##")
    if st.button("🎯 Create My Success Roadmap", help="Start your personalized journey"):
        st.session_state['page'] = 'quiz_page'

def psychometric_test_page():
    st.title("Psychometric Test")
    st.write("Please answer the following questions to help us understand your personality and mindset.")
    questions = {
        "How do you prefer working?": ["Independently", "In a team", "Depends on the task"],
        "What motivates you most?": ["Learning new things", "Achieving goals", "Helping others", "Recognition"],
        "Are you comfortable with uncertainty and change?": ["Yes", "No", "Sometimes"],
        "How do you handle challenges?": ["Face them head-on", "Seek help", "Avoid if possible", "Analyze and plan"]
    }
    answers = {}
    for q, options in questions.items():
        answers[q] = st.radio(q, options, key=q)
    if st.button("Next: Skillset Quiz"):
        st.session_state['psychometric_answers'] = answers
        st.session_state['page'] = 'skillset_quiz_page'

def skillset_quiz_page():
    st.title("Skillset Quiz")
    st.write("Select or enter your skills. You can add multiple skills.")
    skill_options = [
        "Python", "JavaScript", "Machine Learning", "Data Analysis",
        "React", "Node.js", "SQL", "Cloud Computing", "DevOps",
        "UI/UX Design", "Communication", "Project Management"
    ]
    selected_skills = st.multiselect("Select your skills from the list:", skill_options)
    additional_skills = st.text_input("Or enter other skills separated by commas:")
    if additional_skills:
        additional_skills_list = [s.strip() for s in additional_skills.split(",") if s.strip()]
    else:
        additional_skills_list = []
    all_skills = list(set(selected_skills + additional_skills_list))
    if st.button("Generate Career Roadmap"):
        if not all_skills:
            st.error("Please select or enter at least one skill.")
        else:
            st.session_state['selected_skills'] = all_skills
            st.session_state['page'] = 'career_map_page'

def career_map_page():
    st.title("Your Personalized Career Roadmap")
    psychometric_answers = st.session_state.get('psychometric_answers', {})
    selected_skills = st.session_state.get('selected_skills', [])
    if not selected_skills:
        st.error("No skills found. Please complete the skillset quiz.")
        return

    prompt = f"""
    I have a student with the following profile:
    Psychometric answers: {psychometric_answers}
    Skills: {selected_skills}
    Generate a personalized career roadmap including:
    1. Recommended career paths
    2. Skills to learn (with priority and reason)
    3. Suggested micro-projects
    4. Tips for internships or hands-on experience
    Output ONLY the response in JSON format.
    """

    with st.spinner("Generating your career roadmap. Please wait..."):
        model = genai.GenerativeModel("gemini-1.5-flash")
        chat = model.start_chat(history=[])
        response = chat.send_message(prompt)
        response_text = response.text

    st.subheader("Raw AI response (for debugging):")
    st.text(response_text)

    response_text = response_text.strip()
    # Remove markdown code fences robustly
    response_text = re.sub(r"^```(?:json)?", "", response_text, flags=re.IGNORECASE)
    response_text = re.sub(r"```$", "", response_text)
    # Check for empty response
    if not response_text or response_text.lower() in ["none", "null", "undefined"]:
        st.error("AI did not return a valid response. Please try again or check your API key.")
        st.stop()
    try:
        career_data = json.loads(response_text)
    except Exception as e:
        st.error(f"Failed to parse AI response: {e}\nRaw response: {response_text}")
        st.stop()

    roadmap = career_data.get('careerRoadmap') or {}

    # Psychometric answers
    st.subheader("Psychometric Answers")
    for q, a in career_data.get('studentProfile', {}).get('psychometricAnswers', {}).items():
        st.write(f"- **{q}:** {a}")

    # Skills to Learn table
    st.subheader("Skills to Learn")
    skills_to_learn = roadmap.get('skillsToLearn') or {}
    if isinstance(skills_to_learn, dict):
        skills = []
        for priority in ["highPriority", "mediumPriority", "lowPriority"]:
            for skill_item in skills_to_learn.get(priority) or []:
                if isinstance(skill_item, dict):
                    skills.append({
                        "Skill": skill_item.get("skill", ""),
                        "Priority": priority.capitalize(),
                        "Reason": skill_item.get("reason", "")
                    })
        df = pd.DataFrame(skills)
        st.table(df)
    elif isinstance(skills_to_learn, list):
        def flatten_skills_for_display(skill_list):
            flat = []
            for s in skill_list:
                if isinstance(s, dict):
                    flat.append(s.get('skill') or s.get('name') or str(s))
                else:
                    flat.append(str(s))
            return flat
        st.write(", ".join(flatten_skills_for_display(skills_to_learn)))
    else:
        st.write("No skills to learn data available.")

    # Recommended Career Paths
    st.subheader("Recommended Career Paths")
    rec_careers = roadmap.get('recommendedCareerPaths') or []
    for career in rec_careers:
        if isinstance(career, dict):
            title = career.get("title") or career.get("path")
            desc = career.get("description", "")
        else:
            title = str(career)
            desc = ""
        if title and str(title).lower() != "none":
            st.markdown(f"### {title}\n{desc}")

    # Suggested Micro-Projects
    st.subheader("Suggested Micro-Projects")
    projects = roadmap.get('suggestedMicroProjects') or []
    for i, proj in enumerate(projects):
        if isinstance(proj, dict):
            title = proj.get("title") or proj.get("project")
            desc = proj.get("description", "")
        else:
            title = str(proj)
            desc = ""
        if title and str(title).lower() != "none":
            with st.expander(f"{i+1}. {title}"):
                st.write(desc)

    # Tips for Internships
    st.subheader("Tips for Internships or Hands-On Experience")
    tips = roadmap.get('tipsForInternshipsOrHandsOnExperience') or []
    for i, tip in enumerate(tips):
        st.write(f"{i+1}. {tip}")

def main():
    if 'page' not in st.session_state:
        st.session_state['page'] = 'landing_page'

    if st.session_state['page'] == 'landing_page':
        landing_page()
    elif st.session_state['page'] == 'quiz_page':
        psychometric_test_page()
    elif st.session_state['page'] == 'skillset_quiz_page':
        skillset_quiz_page()
    elif st.session_state['page'] == 'career_map_page':
        career_map_page()

if __name__ == "__main__":
    main()
