# Generate Portfolio Projects

Analyze skill gaps from job listings and generate detailed project guides to fill them.

## Instructions

1. Run the project generator:
   ```
   cd /Users/aniketsw/workspaces/mscm && python -c "
   from src.projects import identify_skill_gaps, generate_all_projects
   import json

   gaps = identify_skill_gaps()
   print('SKILL_GAPS:')
   for name, count in gaps:
       print(f'  {name}: requested in {count} jobs')

   projects = generate_all_projects()
   print(f'\nGENERATED {len(projects)} projects:')
   for p in projects:
       print(f'  - {p[\"title\"]} ({p[\"duration\"]}) → {p[\"path\"]}')
   "
   ```

2. Present the generated projects to the user with:
   - Which skill gap each fills
   - How many job listings request that skill
   - Estimated time to complete
   - The resume line they'll get from completing it

3. If specific gaps don't have pre-built templates, generate a custom project guide inline:
   - Title and overview
   - Step-by-step instructions (beginner-friendly)
   - Tools needed (free options only)
   - Expected output / deliverable
   - Resume line to add
   - Interview talking points

4. Save any newly generated projects to `projects/<skill_name>/README.md`
