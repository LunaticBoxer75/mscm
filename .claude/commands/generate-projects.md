# Generate Portfolio Projects

Analyze skill gaps from job listings and build complete project packages with full documentation.

## Instructions

1. First, identify gaps from scored jobs:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.projects import identify_skill_gaps
   gaps = identify_skill_gaps()
   print('SKILL_GAPS:')
   for name, count in gaps:
       print(f'  {name}: requested in {count} jobs')
   "
   ```

2. Check which projects already exist:
   ```
   ls /Users/aniketsw/workspaces/mscm/projects/*/README.md 2>/dev/null
   ```

3. **IMPORTANT — Only generate a project if:**
   - A skill gap is genuinely present (appears in 15%+ of top job listings)
   - No existing project already covers it
   - The user hasn't explicitly skipped or rejected it previously

4. For each NEW gap that warrants a project, **build the complete project** — not just an idea:
   - `projects/<skill-name>/README.md` — Full beginner-friendly walkthrough (see existing projects for format)
   - `projects/<skill-name>/<main-script>` — Complete runnable code
   - `projects/<skill-name>/requirements.txt` — Dependencies
   - Include: what you'll build, why it matters, every step from install to completion, resume line, interview talking points

5. After generating, update the projects index:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.projects import generate_all_projects
   projects = generate_all_projects()
   for p in projects:
       print(f'  ✓ {p[\"title\"]} → {p[\"path\"]}')
   "
   ```

6. Present what was generated to the user.

## Project Quality Bar
Each project must be:
- Completable by someone with ZERO prior experience in that tool
- Produces a tangible portfolio artifact (image, dashboard, report)
- Includes a copy-paste resume bullet point
- Uses only free tools
- Takes 1-2 weeks at ~2hr/day
