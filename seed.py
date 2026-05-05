import os
from app import create_app
from api.tags_models import db, User, Category, Post, Tag

def seed_database():
    """Seeds the database with test users and sample posts for manual UI testing."""
    os.environ.setdefault("SECRET_KEY", "demo-seed-secret-key")
    app = create_app(testing=False)
    with app.app_context():
        # app.py already calls db.create_all() and seeds default categories
        print("Seeding database...")
        
        # Check if already seeded to prevent duplicates
        if User.query.filter_by(username="alice").first():
            print("Database is already seeded with demo users. Skipping.")
            return

        # Create demo users
        alice = User(username="alice", email="alice@student.uwa.edu.au", password_hash="test_password", email_confirmed=True)
        bob = User(username="bob", email="bob@student.uwa.edu.au", password_hash="test_password", email_confirmed=True)
        carol = User(username="carol", email="carol@student.uwa.edu.au", password_hash="test_password", email_confirmed=True)
        
        db.session.add_all([alice, bob, carol])
        db.session.commit()
        
        print("Created demo users: alice, bob, carol")

        # Get existing categories (these should be seeded by app.py)
        coding_cat = Category.query.filter_by(slug="coding").first()
        music_cat = Category.query.filter_by(slug="music").first()
        languages_cat = Category.query.filter_by(slug="languages").first()
        
        if not coding_cat or not music_cat or not languages_cat:
            print("Warning: Expected categories not found. Skipping post seeding.")
            return

        # Create some tags
        python_tag = Tag(slug="python", label="Python")
        guitar_tag = Tag(slug="guitar", label="Guitar")
        spanish_tag = Tag(slug="spanish", label="Spanish")
        
        db.session.add_all([python_tag, guitar_tag, spanish_tag])
        db.session.flush()

        # Create demo posts
        post1 = Post(
            title="I can teach Python for Data Science", 
            description="I am looking for someone to teach me acoustic guitar in exchange for advanced Python lessons.",
            category_id=coding_cat.id,
            owner_id=alice.id,
            status="open"
        )
        post1.tags.append(python_tag)
        
        post2 = Post(
            title="Guitar lessons available",
            description="I have been playing guitar for 5 years. I need help with my Java assignments, but happy to help anyone else learn.",
            category_id=music_cat.id,
            owner_id=bob.id,
            status="open"
        )
        post2.tags.append(guitar_tag)
        
        post3 = Post(
            title="Native Spanish speaker offering conversation practice",
            description="Happy to chat in Spanish for 1 hour a week. I'd love to learn some Python basics if possible!",
            category_id=languages_cat.id,
            owner_id=carol.id,
            status="open"
        )
        post3.tags.append(spanish_tag)
        post3.tags.append(python_tag)
        
        db.session.add_all([post1, post2, post3])
        db.session.commit()
        
        print("Created demo posts for alice, bob, and carol")
        print("==================================================")
        print("Seed complete! You can now log in with the following emails:")
        print("- alice@student.uwa.edu.au")
        print("- bob@student.uwa.edu.au")
        print("- carol@student.uwa.edu.au")
        print("(Use any password, authentication is loosely enforced in demo)")
        print("==================================================")

if __name__ == "__main__":
    seed_database()
