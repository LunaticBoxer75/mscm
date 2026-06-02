"""Generate a JavaScript bookmarklet that auto-fills ATS application forms.

When the user clicks the bookmarklet on any Workday/Greenhouse/Lever/iCIMS form,
the JS scans for known field names and fills them with profile data.
"""

import json
import urllib.parse
from pathlib import Path

CONFIG_DIR = Path(__file__).parent.parent / "config"


def get_profile_data():
    """Get Bhumika's profile data for form filling."""
    with open(CONFIG_DIR / "profile.json") as f:
        profile = json.load(f)

    candidate = profile.get("candidate", {})
    return {
        "firstName": "Bhumika",
        "lastName": "Choudhary",
        "fullName": candidate.get("name", "Bhumika Choudhary"),
        "email": candidate.get("email", ""),
        "phone": candidate.get("phone", ""),
        "linkedin": f"https://www.linkedin.com/in/{candidate.get('linkedin', 'bhummika')}/",
        "city": "Seattle",
        "state": "WA",
        "country": "United States",
        "currentLocation": candidate.get("location", "Hyderabad, India"),
        "visaStatus": "F1 Student (STEM OPT eligible from June 2027)",
        "needsSponsorship": "Yes",
        "authorizedToWork": "Yes (will be after OPT EAD)",
        "salaryExpectation": "100000",
        "earliestStartDate": "2027-06-01",
        "school": "University of Washington - Foster School of Business",
        "degree": "Master of Supply Chain Management (MSCM)",
        "graduationDate": "2027-05",
    }


def generate_bookmarklet_js():
    """Generate the JavaScript that auto-fills form fields."""
    data = get_profile_data()

    # Build field selectors mapping
    js_template = """
(function(){
  var data = %s;

  var fieldMap = {
    // Name
    'firstName': data.firstName, 'first_name': data.firstName, 'fname': data.firstName, 'givenName': data.firstName,
    'lastName': data.lastName, 'last_name': data.lastName, 'lname': data.lastName, 'familyName': data.lastName,
    'fullName': data.fullName, 'full_name': data.fullName, 'name': data.fullName,
    // Contact
    'email': data.email, 'emailAddress': data.email, 'email_address': data.email,
    'phone': data.phone, 'phoneNumber': data.phone, 'phone_number': data.phone, 'mobile': data.phone,
    'linkedin': data.linkedin, 'linkedinUrl': data.linkedin, 'linkedin_url': data.linkedin, 'linkedInProfile': data.linkedin,
    // Location
    'city': data.city, 'state': data.state, 'country': data.country,
    'currentCity': data.city, 'current_city': data.city,
    // Visa
    'visa': data.visaStatus, 'visaStatus': data.visaStatus, 'workAuthorization': data.authorizedToWork,
    'requireSponsorship': data.needsSponsorship, 'sponsorship': data.needsSponsorship,
    'authorized': data.authorizedToWork,
    // Misc
    'salary': data.salaryExpectation, 'salaryExpectation': data.salaryExpectation, 'expectedSalary': data.salaryExpectation,
    'startDate': data.earliestStartDate, 'availability': data.earliestStartDate,
    'school': data.school, 'university': data.school, 'institution': data.school,
    'degree': data.degree, 'major': data.degree,
  };

  var filled = 0;
  var inputs = document.querySelectorAll('input, textarea, select');
  inputs.forEach(function(el){
    var name = (el.name || el.id || '').toLowerCase();
    var aria = (el.getAttribute('aria-label') || '').toLowerCase();
    var label = '';
    var lblEl = el.labels && el.labels[0];
    if (lblEl) label = lblEl.innerText.toLowerCase();
    var allText = name + ' ' + aria + ' ' + label;

    Object.keys(fieldMap).forEach(function(key){
      if (allText.indexOf(key.toLowerCase()) !== -1 && !el.value) {
        var val = fieldMap[key];
        if (val) {
          el.value = val;
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
          el.dispatchEvent(new Event('blur', { bubbles: true }));
          filled++;
        }
      }
    });
  });

  alert('MSCM Auto-Fill: filled ' + filled + ' fields. Review before submitting!');
})();
""" % json.dumps(data)

    # Minify slightly and URL-encode
    minified = " ".join(js_template.split())
    encoded = "javascript:" + urllib.parse.quote(minified, safe="(){}[],;:.!?'+=&|<>%@/")
    return encoded, js_template


def get_bookmarklet_html():
    """Return HTML snippet with the draggable bookmarklet link."""
    encoded, _ = generate_bookmarklet_js()
    return f'<a href="{encoded}" class="bookmarklet">📌 MSCM Auto-Fill</a>'
