"""
add_categories.py – Upsert the full category list without wiping existing data.

Run once after extending the category set:
    .venv/bin/python add_categories.py
"""

from app import app, db
from models import Category


CATEGORIES = [
    # slug                label                       sort_order
    ('coding',      'Coding & IT',               10),
    ('academic',    'Academic / Tutoring',        15),
    ('language',    'Languages',                  20),
    ('business',    'Business & Finance',         25),
    ('engineering', 'Engineering & Science',      30),
    ('music',       'Music & Arts',               35),
    ('design',      'Design & Creative',          40),
    ('sports',      'Sports & Fitness',           45),
    ('health',      'Health & Wellness',          50),
    ('cooking',     'Cooking & Food',             55),
    ('career',      'Career & Professional',      60),
    ('gaming',      'Gaming',                     65),
    ('other',       'Other',                      99),
]


def run():
    with app.app_context():
        added   = 0
        updated = 0
        for slug, label, order in CATEGORIES:
            cat = Category.query.filter_by(slug=slug).first()
            if cat:
                # Update label and sort_order in case they changed
                if cat.label != label or cat.sort_order != order:
                    cat.label      = label
                    cat.sort_order = order
                    updated += 1
            else:
                db.session.add(Category(slug=slug, label=label, sort_order=order))
                added += 1
        db.session.commit()
        print(f'Done. Added: {added}  Updated: {updated}')
        for c in Category.query.order_by(Category.sort_order).all():
            print(f'  [{c.sort_order:3d}] {c.slug:<14} {c.label}')


if __name__ == '__main__':
    run()
