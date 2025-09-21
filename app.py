import streamlit as st
from dotenv import load_dotenv
import os
import google.generativeai as genai
import json
import re
import networkx as nx
import plotly.graph_objects as go

# Load environment variables from .env file
load_dotenv()

# Get your API key
api_key = os.getenv("GEMINI_API_KEY")
if api_key is None:
    st.error("GEMINI_API_KEY not set. Please add your API key to the .env file.")
    st.stop()

# Configure Gemini API key
genai.configure(api_key=api_key)

# Page configuration
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


def flatten_skills(skill_list):
    """Ensure skills are always strings, not dicts."""
    flat = []
    for s in skill_list:
        if isinstance(s, dict):
            flat.append(s.get('name') or s.get('skill') or json.dumps(s))
        else:
            flat.append(str(s))
    return flat


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
    2. Skills to learn (with priority)
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

    # Remove markdown JSON fences robustly
    response_text = response_text.strip()
    response_text = re.sub(r"^```(?:json)?", "", response_text, flags=re.IGNORECASE)
    response_text = re.sub(r"```$", "", response_text)

    try:
        career_data = json.loads(response_text)
    except Exception as e:
        st.error(f"Failed to parse AI response: {e}")
        st.stop()

    roadmap = career_data.get('careerRoadmap') or career_data.get('roadmap') or {}
    careers = roadmap.get('recommendedCareerPaths') or roadmap.get('recommended_career_paths') or []
    skills_to_learn = roadmap.get('skillsToLearn') or roadmap.get('skills_to_learn') or {}
    high_priority = flatten_skills(skills_to_learn.get('highPriority') or skills_to_learn.get('high_priority') or [])
    medium_priority = flatten_skills(skills_to_learn.get('mediumPriority') or skills_to_learn.get('medium_priority') or [])
    low_priority = flatten_skills(skills_to_learn.get('lowPriority') or skills_to_learn.get('low_priority') or [])
    selected_skills = flatten_skills(selected_skills)

    all_skills = list(set(high_priority + medium_priority + low_priority + selected_skills))

    G = nx.DiGraph()
    for skill in all_skills:
        G.add_node(skill, type='skill')
    for career in careers:
        title = career.get('title') if isinstance(career, dict) else str(career)
        G.add_node(title, type='career')
        for skill in all_skills:
            G.add_edge(skill, title)

    pos = nx.spring_layout(G, seed=42)
    edge_x, edge_y = [], []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=1, color='gray'),
        mode='lines'
    )
    node_trace = go.Scatter(
        x=[pos[n][0] for n in G.nodes()],
        y=[pos[n][1] for n in G.nodes()],
        mode='markers+text',
        text=list(G.nodes()),
        marker=dict(
            size=15,
            color=['blue' if G.nodes[n]['type'] == 'skill' else 'green' for n in G.nodes()]
        )
    )
    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title='Skill → Career Map',
        showlegend=False,
        hovermode='closest',
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
    )
    st.plotly_chart(fig, use_container_width=True)


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