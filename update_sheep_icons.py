"""
Quick script to update animal icons for sheep devices
"""

import os

files_to_update = [
    "app/templates/dashboard/animals.html",
    "app/templates/dashboard/animal_detail.html",
    "app/templates/dashboard/analytics.html"
]

for filepath in files_to_update:
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        continue
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count replacements
    count_before = content.count('🐄')
    
    # For animals.html - update the icon in the table
    if 'animals.html' in filepath:
        # Replace the static cow emoji with conditional logic
        content = content.replace(
            '<span class="text-2xl mr-2">🐄</span>',
            "{% if animal.device_id.startswith('SHEEP') %}<span class=\"text-2xl mr-2\">🐑</span>{% else %}<span class=\"text-2xl mr-2\">🐄</span>{% endif %}"
        )
    
    # For animal_detail.html - update the header icon
    elif 'animal_detail.html' in filepath:
        content = content.replace(
            '<span class="text-6xl mr-4">🐄</span>',
            "{% if animal.device_id.startswith('SHEEP') %}<span class=\"text-6xl mr-4\">🐑</span>{% else %}<span class=\"text-6xl mr-4\">🐄</span>{% endif %}"
        )
    
    # For analytics.html - update the alerting animals icon
    elif 'analytics.html' in filepath:
        # This one is trickier - need to check the device_id in the loop
        content = content.replace(
            '<span class="text-2xl mr-2">🐄</span>',
            "{% if animal[0].startswith('SHEEP') %}<span class=\"text-2xl mr-2\">🐑</span>{% else %}<span class=\"text-2xl mr-2\">🐄</span>{% endif %}"
        )
    
    count_after = content.count('🐄')
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Updated {filepath}")
    print(f"   Cow emojis before: {count_before}, after: {count_after}")

print("\n✅ All files updated! Restart the server to see changes.")
