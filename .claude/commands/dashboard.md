# Launch Job Search Dashboard

Start the Streamlit web dashboard for viewing jobs, tracking applications, and exploring results.

## Instructions

1. Start the dashboard:
   ```
   cd /Users/aniketsw/workspaces/mscm && streamlit run app.py --server.port 8501
   ```

2. Tell the user: "Dashboard running at http://localhost:8501"

3. The dashboard shows:
   - Metrics bar (total jobs, scored, high matches, etc.)
   - 5 tabs: Seattle FT, Seattle Internships, National FT, National Internships, All Jobs
   - Score filtering sidebar
   - Job detail view with score breakdown
   - Company leaderboard
