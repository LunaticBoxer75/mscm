"""Referral / outreach message text. Kept free of heavy imports so the dashboard can
use it without loading the scraper."""

from pathlib import Path
def _years():
    import json
    try:
        return json.loads((Path(__file__).parent.parent / "config" / "profile.json").read_text()
                          )["experience_summary"]["years"]
    except (OSError, KeyError, ValueError):
        return 4


def referral_note(title, company):
    """LinkedIn connection note — must stay under 300 chars, and can't carry an attachment."""
    note = (f"Hi [Name], I'm Bhumika, an MSCM student at UW Foster with {_years()} years in risk & "
            f"operations at Uber. I'm applying for the {title} role at {company} — would you be open "
            f"to referring me? Happy to send my resume. Thank you!")
    if len(note) > 300:  # long titles: drop the role name rather than overflow
        note = (f"Hi [Name], I'm Bhumika, an MSCM student at UW Foster with {_years()} years in risk & "
                f"operations at Uber. I'm applying to a role at {company} — would you be open to "
                f"referring me? Happy to send my resume. Thank you!")
    return note


def referral_message(title, company):
    """Longer version for a LinkedIn message, InMail or email, where the resume can be attached."""
    return (f"Hi [Name],\n\nI'm Bhumika, an MSCM student at UW Foster (graduating June 2027) with "
            f"{_years()} years of risk, compliance and operations experience at Uber. I'm very interested "
            f"in the {title} role at {company} and would really appreciate a referral if you think my "
            f"background could be a fit. I have attached my resume with this message.\n\nThank you!\n"
            f"Bhumika")
