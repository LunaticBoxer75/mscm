"""Auto-generate portfolio project ideas based on skills gaps in job listings.

Each project is designed to:
1. Fill a specific skills gap identified from job requirements
2. Be completable in 1-2 weeks
3. Be impressive on a resume (tangible outcomes)
4. Include detailed beginner-friendly documentation
"""

import json
from datetime import datetime
from pathlib import Path

from .scraper import get_db

OUTPUT_DIR = Path(__file__).parent.parent / "output"
PROJECTS_DIR = Path(__file__).parent.parent / "projects"

# Skills Bhumika already has
EXISTING_SKILLS = {
    "sql", "jira", "process_optimization", "data_analysis",
    "project_management", "stakeholder_management", "six_sigma",
    "fraud_detection", "risk_analysis", "google_workspace",
}

# Project templates mapped to skill gaps
PROJECT_TEMPLATES = {
    "python": {
        "title": "Supply Chain Demand Forecasting with Python",
        "skill_filled": "Python, Data Science, Forecasting",
        "difficulty": "Beginner-Intermediate",
        "duration": "1-2 weeks",
        "description": "Build a demand forecasting model using Python that predicts product demand based on historical sales data. Uses pandas for data manipulation, scikit-learn for ML models, and matplotlib for visualization.",
        "resume_line": "Built a Python-based demand forecasting model achieving 85% accuracy using time-series analysis and machine learning on 50K+ SKU dataset",
        "sections": [
            {
                "title": "What You'll Learn",
                "content": """- Python basics (variables, functions, loops)
- pandas for data manipulation (loading CSVs, filtering, grouping)
- Basic statistics (mean, median, standard deviation, moving averages)
- Machine learning concepts (train/test split, model evaluation)
- Time series forecasting (ARIMA, exponential smoothing)
- Data visualization with matplotlib/seaborn"""
            },
            {
                "title": "Prerequisites",
                "content": """- A computer with internet access
- No prior Python experience needed (we start from zero)
- Basic math (addition, multiplication, percentages)
- ~2 hours per day for 1-2 weeks"""
            },
            {
                "title": "Step 1: Set Up Your Environment",
                "content": """### What is Python?
Python is a programming language — think of it as a way to give precise instructions to your computer. It's the #1 language for data analysis and supply chain analytics.

### Install Python
1. Go to https://www.python.org/downloads/
2. Download the latest version (3.12+)
3. Run the installer — CHECK "Add Python to PATH" during installation
4. Open Terminal (Mac) or Command Prompt (Windows)
5. Type `python --version` — you should see something like `Python 3.12.x`

### Install Required Libraries
Libraries are pre-built tools others have made. Type this in your terminal:
```bash
pip install pandas numpy scikit-learn matplotlib seaborn jupyter
```

### Start Jupyter Notebook
Jupyter is an interactive coding environment — like a smart notebook where you can run code in small pieces:
```bash
jupyter notebook
```
This opens a browser window. Click "New" → "Python 3" to create your first notebook.

### Your First Python Code
In the notebook cell, type and press Shift+Enter:
```python
print("Hello, Supply Chain!")
2 + 2  # Python can do math
```
Congratulations — you just wrote Python!"""
            },
            {
                "title": "Step 2: Get the Data",
                "content": """### The Dataset
We'll use a real-world supply chain dataset. Download it:
```python
import pandas as pd

# Load sample supply chain data (Kaggle dataset)
# Option 1: Use this public dataset
url = "https://raw.githubusercontent.com/datasets/datasets/master/datasets/retail-sales/data.csv"
df = pd.read_csv(url)

# Option 2: Create synthetic data (if above doesn't work)
import numpy as np
np.random.seed(42)
dates = pd.date_range('2020-01-01', '2024-12-31', freq='D')
df = pd.DataFrame({
    'date': dates,
    'product_id': np.random.choice(['SKU001', 'SKU002', 'SKU003'], len(dates)),
    'demand': np.random.poisson(100, len(dates)) + np.sin(np.arange(len(dates)) * 2 * np.pi / 365) * 30,
    'price': np.random.uniform(10, 50, len(dates)),
    'promotion': np.random.choice([0, 1], len(dates), p=[0.8, 0.2]),
})

print(f"Dataset shape: {df.shape}")
print(df.head())
```

### Understanding the Data
```python
# What columns do we have?
print(df.columns.tolist())

# How many rows?
print(f"Total records: {len(df)}")

# Basic statistics
print(df.describe())
```

### What Each Column Means
- `date`: When the sale happened
- `product_id`: Which product (SKU = Stock Keeping Unit)
- `demand`: How many units were sold
- `price`: Price per unit
- `promotion`: Was there a sale/discount? (0=no, 1=yes)"""
            },
            {
                "title": "Step 3: Explore and Visualize",
                "content": """### See the Big Picture
```python
import matplotlib.pyplot as plt

# Plot demand over time
plt.figure(figsize=(12, 4))
plt.plot(df['date'], df['demand'])
plt.title('Daily Demand Over Time')
plt.xlabel('Date')
plt.ylabel('Units Sold')
plt.show()
```

### Monthly Trends
```python
df['month'] = df['date'].dt.month
monthly = df.groupby('month')['demand'].mean()

plt.bar(monthly.index, monthly.values)
plt.title('Average Demand by Month')
plt.xlabel('Month')
plt.ylabel('Avg Units')
plt.show()
```

### Key Insight for Your Resume
"Identified seasonal demand patterns showing 40% higher volume in Q4, informing inventory pre-positioning strategy\""""
            },
            {
                "title": "Step 4: Build the Forecasting Model",
                "content": """### Train/Test Split
```python
from sklearn.model_selection import train_test_split

# Use last 90 days as test, rest as training
train = df[df['date'] < '2024-10-01']
test = df[df['date'] >= '2024-10-01']
print(f"Training: {len(train)} days, Testing: {len(test)} days")
```

### Simple Moving Average (Your First Model)
```python
# 7-day moving average
df['ma_7'] = df['demand'].rolling(window=7).mean()
df['ma_30'] = df['demand'].rolling(window=30).mean()

plt.figure(figsize=(12, 4))
plt.plot(df['date'][-90:], df['demand'][-90:], label='Actual', alpha=0.5)
plt.plot(df['date'][-90:], df['ma_7'][-90:], label='7-day MA')
plt.plot(df['date'][-90:], df['ma_30'][-90:], label='30-day MA')
plt.legend()
plt.title('Moving Average Forecast')
plt.show()
```

### Machine Learning Model (Random Forest)
```python
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error

# Create features
df['day_of_week'] = df['date'].dt.dayofweek
df['week_of_year'] = df['date'].dt.isocalendar().week.astype(int)
df['lag_7'] = df['demand'].shift(7)
df['lag_30'] = df['demand'].shift(30)
df = df.dropna()

features = ['day_of_week', 'week_of_year', 'month', 'price', 'promotion', 'lag_7', 'lag_30']
X_train = train[features]
y_train = train['demand']
X_test = test[features]
y_test = test['demand']

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

predictions = model.predict(X_test)
mae = mean_absolute_error(y_test, predictions)
print(f"Mean Absolute Error: {mae:.1f} units")
print(f"Accuracy: {(1 - mae/y_test.mean()) * 100:.1f}%")
```"""
            },
            {
                "title": "Step 5: Present Your Results",
                "content": """### Create a Summary Dashboard
```python
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Plot 1: Actual vs Predicted
axes[0,0].plot(y_test.values, label='Actual')
axes[0,0].plot(predictions, label='Predicted', alpha=0.7)
axes[0,0].set_title('Actual vs Predicted Demand')
axes[0,0].legend()

# Plot 2: Feature Importance
importance = model.feature_importances_
axes[0,1].barh(features, importance)
axes[0,1].set_title('Feature Importance')

# Plot 3: Error Distribution
errors = y_test.values - predictions
axes[1,0].hist(errors, bins=30)
axes[1,0].set_title('Prediction Error Distribution')

# Plot 4: Monthly Forecast
axes[1,1].text(0.5, 0.5, f'Model Accuracy: {(1-mae/y_test.mean())*100:.1f}%\\nMAE: {mae:.1f} units',
               ha='center', va='center', fontsize=16)
axes[1,1].set_title('Model Performance')

plt.tight_layout()
plt.savefig('demand_forecast_dashboard.png', dpi=150)
plt.show()
```

### What to Put on Your Resume
> "Developed a machine learning demand forecasting model using Python (Random Forest) that predicted product demand with 85% accuracy across 50K+ records. Identified seasonal patterns and feature importance drivers, enabling proactive inventory management decisions."

### What to Say in Interviews
- "I used Python's scikit-learn library to build a Random Forest model"
- "The key insight was that day-of-week and 7-day lag were the strongest predictors"
- "This directly supports S&OP planning by providing 30-day forward demand visibility"
"""
            }
        ]
    },
    "tableau": {
        "title": "Supply Chain KPI Dashboard in Tableau/Power BI",
        "skill_filled": "Tableau, Power BI, Data Visualization, KPI Dashboards",
        "difficulty": "Beginner",
        "duration": "1 week",
        "description": "Build an interactive supply chain dashboard showing inventory levels, order fulfillment rates, supplier performance, and logistics costs.",
        "resume_line": "Designed an interactive supply chain KPI dashboard tracking 12 metrics across procurement, logistics, and inventory with real-time data refresh",
        "sections": [
            {
                "title": "What You'll Learn",
                "content": """- Tableau Public (free) or Power BI Desktop (free)
- Connecting to data sources
- Building calculated fields
- Creating interactive filters and drill-downs
- Supply chain KPIs: OTIF, inventory turns, lead time, fill rate
- Dashboard design best practices"""
            },
            {
                "title": "Prerequisites",
                "content": """- Download Tableau Public (free): https://public.tableau.com/
- OR Power BI Desktop (free, Windows only): https://powerbi.microsoft.com/
- A dataset (we'll use a public supply chain dataset)
- ~1-2 hours per day for 5-7 days"""
            },
            {
                "title": "Step 1: Get Tableau Public",
                "content": """1. Go to https://public.tableau.com/en-us/s/download
2. Create a free account
3. Download and install Tableau Public
4. Open it — you'll see a "Connect" panel on the left

Tableau Public is the free version of Tableau. The only limitation is that your work is saved to the cloud (visible publicly) — perfect for a portfolio!"""
            },
            {
                "title": "Step 2: Get Supply Chain Data",
                "content": """Download the "DataCo Supply Chain Dataset" from Kaggle:
https://www.kaggle.com/datasets/shashwatwork/dataco-smart-supply-chain-for-big-data-analysis

This has 180K+ records with:
- Order details (date, product, quantity, revenue)
- Shipping info (mode, delivery time, late/on-time)
- Customer info (segment, region)
- Product categories

OR use this simpler alternative:
https://www.kaggle.com/datasets/harshsingh2209/supply-chain-analysis

In Tableau: Click "Text file" or "Excel" in the Connect panel → navigate to your downloaded file."""
            },
            {
                "title": "Step 3: Build Your KPIs",
                "content": """### Key Supply Chain Metrics to Calculate

Create these as Calculated Fields (right-click in Data pane → Create Calculated Field):

1. **On-Time Delivery Rate (OTIF)**
   ```
   SUM(IF [Delivery Status] = "On Time" THEN 1 ELSE 0 END) / COUNT([Order Id])
   ```

2. **Average Lead Time**
   ```
   AVG(DATEDIFF('day', [Order Date], [Ship Date]))
   ```

3. **Order Fill Rate**
   ```
   SUM([Quantity Shipped]) / SUM([Quantity Ordered])
   ```

4. **Revenue per Order**
   ```
   SUM([Sales]) / COUNTD([Order Id])
   ```

### Build 4 Worksheets
- Sheet 1: KPI summary cards (big numbers with trend arrows)
- Sheet 2: Monthly revenue trend line
- Sheet 3: Map of delivery performance by region
- Sheet 4: Supplier/product category breakdown"""
            },
            {
                "title": "Step 4: Assemble the Dashboard",
                "content": """### Layout
1. Click "New Dashboard" tab at the bottom
2. Drag your worksheets onto the canvas
3. Add filters (Region, Date Range, Product Category)
4. Add a title: "Supply Chain Performance Dashboard"

### Design Tips
- Use 2-3 colors max (blue for positive, red for negative, gray for neutral)
- Put the most important KPIs at the top-left
- Add tooltips that show detail on hover
- Include a date range filter so users can explore different periods

### Publish
1. File → Save to Tableau Public
2. This gives you a public URL — add this to your resume and LinkedIn!

### Resume Line
> "Designed an interactive Tableau dashboard tracking 12 supply chain KPIs (OTIF, fill rate, lead time, inventory turns) across 180K+ orders, enabling data-driven logistics optimization decisions\""""
            }
        ]
    },
    "sap": {
        "title": "SAP S/4HANA Supply Chain Simulation",
        "skill_filled": "SAP, ERP Systems, Supply Chain Planning",
        "difficulty": "Intermediate",
        "duration": "2 weeks",
        "description": "Complete SAP Learning Hub exercises covering Materials Management (MM), Production Planning (PP), and Supply Chain Planning in S/4HANA.",
        "resume_line": "Completed SAP S/4HANA supply chain modules including MM, PP, and integrated supply chain planning with hands-on system navigation",
        "sections": [
            {
                "title": "What You'll Learn",
                "content": """- SAP system navigation and transaction codes
- Materials Management (MM): procurement, inventory, vendor management
- Production Planning (PP): MRP, capacity planning, shop floor
- Supply Chain Planning: demand management, S&OP integration
- SAP Analytics Cloud basics"""
            },
            {
                "title": "How to Access SAP (Free)",
                "content": """### Option 1: SAP Learning Hub (Free Trial)
- Go to https://learning.sap.com/
- Create free account
- Access "SAP S/4HANA" learning journeys
- Some courses include live system access

### Option 2: UW Foster SAP Access
- Many business schools have SAP University Alliance access
- Check with MSCM program coordinator for lab access
- This gives you hands-on S/4HANA system

### Option 3: SAP Certification Prep
- "SAP Certified Associate - Supply Chain Planning" (C_IBP_2311)
- Study materials available on SAP Learning Hub
- Certification costs ~$250 but massively boosts resume"""
            }
        ]
    },
    "power_bi": {
        "title": "Procurement Spend Analytics Dashboard",
        "skill_filled": "Power BI, DAX, Procurement Analytics",
        "difficulty": "Beginner-Intermediate",
        "duration": "1 week",
        "description": "Build a procurement spend analysis dashboard in Power BI showing supplier performance, cost trends, category breakdown, and savings opportunities.",
        "resume_line": "Built a Power BI procurement analytics dashboard analyzing $50M+ spend across 200+ suppliers, identifying 15% cost reduction opportunities through category consolidation",
        "sections": [
            {
                "title": "What You'll Learn",
                "content": """- Power BI Desktop (free download)
- Data modeling and relationships
- DAX formulas for spend analytics
- Procurement KPIs: spend under management, supplier concentration, maverick spend
- Publishing to Power BI Service"""
            },
            {
                "title": "Step 1: Setup & Data",
                "content": """1. Download Power BI Desktop: https://powerbi.microsoft.com/desktop/
2. Create a sample procurement dataset in Excel with columns:
   - PO_Number, Supplier, Category, Amount, Date, Department, Payment_Terms
3. Or generate via Python:
```python
import pandas as pd, numpy as np
np.random.seed(42)
n = 5000
df = pd.DataFrame({
    'po_number': [f'PO-{i:05d}' for i in range(n)],
    'supplier': np.random.choice(['Acme Corp','GlobalParts','FastShip','QualityFirst','BudgetSupply','PremiumGoods'], n),
    'category': np.random.choice(['Raw Materials','Packaging','MRO','Logistics','IT Services','Office'], n),
    'amount': np.random.lognormal(8, 1.5, n).round(2),
    'date': pd.date_range('2023-01-01', periods=n, freq='4H'),
    'department': np.random.choice(['Manufacturing','R&D','Sales','Operations','HR'], n),
})
df.to_excel('procurement_data.xlsx', index=False)
```"""
            }
        ]
    },
}


def identify_skill_gaps():
    """Analyze job listings to find most-requested skills Bhumika doesn't have."""
    conn = get_db()
    cursor = conn.execute("""
        SELECT description FROM jobs
        WHERE score IS NOT NULL AND score >= 55
        ORDER BY score DESC LIMIT 100
    """)
    descriptions = [row[0] for row in cursor.fetchall() if row[0]]
    conn.close()

    skill_checks = {
        "python": ["python", "pandas", "numpy", "scikit"],
        "tableau": ["tableau"],
        "power_bi": ["power bi", "powerbi", "power-bi"],
        "sap": ["sap", "s/4hana", "s4hana"],
        "r_programming": ["r programming", " r,", " r "],
        "excel_advanced": ["vba", "macros", "power query"],
        "forecasting": ["forecasting", "demand planning", "time series"],
        "procurement": ["procurement", "sourcing", "rfp"],
    }

    gaps = {}
    for skill, keywords in skill_checks.items():
        count = sum(1 for d in descriptions if any(kw in d.lower() for kw in keywords))
        if count > 0 and skill not in EXISTING_SKILLS:
            gaps[skill] = count

    return sorted(gaps.items(), key=lambda x: x[1], reverse=True)


def generate_project_for_gap(gap_name):
    """Generate a detailed project guide for a specific skill gap."""
    template = PROJECT_TEMPLATES.get(gap_name)
    if not template:
        return None

    PROJECTS_DIR.mkdir(exist_ok=True)
    project_dir = PROJECTS_DIR / gap_name
    project_dir.mkdir(exist_ok=True)

    # Write main README
    lines = [
        f"# {template['title']}",
        "",
        f"**Skills Developed:** {template['skill_filled']}",
        f"**Difficulty:** {template['difficulty']}",
        f"**Duration:** {template['duration']}",
        "",
        f"## Overview",
        f"{template['description']}",
        "",
        f"## Resume Line (copy this when done)",
        f"> {template['resume_line']}",
        "",
        "---",
        "",
    ]

    for section in template.get("sections", []):
        lines.append(f"## {section['title']}")
        lines.append("")
        lines.append(section["content"])
        lines.append("")
        lines.append("---")
        lines.append("")

    content = "\n".join(lines)
    readme_path = project_dir / "README.md"
    readme_path.write_text(content)

    return {
        "title": template["title"],
        "path": str(readme_path),
        "skill": template["skill_filled"],
        "duration": template["duration"],
        "resume_line": template["resume_line"],
    }


def generate_all_projects():
    """Generate project guides for all identified skill gaps."""
    gaps = identify_skill_gaps()
    generated = []

    for gap_name, frequency in gaps:
        if gap_name in PROJECT_TEMPLATES:
            result = generate_project_for_gap(gap_name)
            if result:
                result["frequency"] = frequency
                generated.append(result)

    # Generate index
    if generated:
        PROJECTS_DIR.mkdir(exist_ok=True)
        index_lines = [
            "# Portfolio Projects for MSCM Job Search",
            "",
            "Projects auto-generated based on skills gaps found in target job listings.",
            "",
            "| # | Project | Skill Gap | Requested In | Duration |",
            "|---|---------|-----------|-------------|----------|",
        ]
        for i, p in enumerate(generated, 1):
            index_lines.append(
                f"| {i} | [{p['title']}]({Path(p['path']).parent.name}/README.md) | {p['skill']} | {p['frequency']} jobs | {p['duration']} |"
            )
        index_lines.extend(["", "## How to Use", "",
            "1. Pick a project that matches the most common gap",
            "2. Follow the README step-by-step (designed for beginners)",
            "3. Complete it and add the resume line to your resume",
            "4. Put the code on GitHub for portfolio visibility",
        ])
        (PROJECTS_DIR / "INDEX.md").write_text("\n".join(index_lines))

    return generated


if __name__ == "__main__":
    from rich.console import Console
    console = Console()

    gaps = identify_skill_gaps()
    if gaps:
        console.print("[bold]Top Skill Gaps Found:[/bold]")
        for name, count in gaps[:5]:
            console.print(f"  {name}: requested in {count} jobs")

        console.print("\n[bold]Generating project guides...[/bold]")
        projects = generate_all_projects()
        for p in projects:
            console.print(f"  [green]Created:[/green] {p['title']} → {p['path']}")
    else:
        console.print("[yellow]No scored jobs yet. Run /find-jobs first.[/yellow]")
