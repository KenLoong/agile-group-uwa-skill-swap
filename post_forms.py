# =============================================================================
# WTForms definitions for Posts & Discovery (create / edit flows)
# =============================================================================
from __future__ import annotations

from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import SelectField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional


class CreatePostForm(FlaskForm):
    """Server-side validated create flow; category choices injected per request."""

    title = StringField(
        "Skill title",
        validators=[DataRequired(message="Give your post a short title."), Length(max=100)],
    )
    category_id = SelectField(
        "Category",
        coerce=int,
        validators=[DataRequired(message="Pick one category.")],
    )
    description = TextAreaField(
        "Description",
        validators=[
            DataRequired(message="Describe what you are offering."),
            Length(max=20_000),
        ],
        render_kw={"rows": 6},
    )
    tags = StringField(
        "Tags",
        validators=[Optional(), Length(max=500)],
        description="Comma-separated keywords, e.g. python, beginner, cits5505.",
    )
    cover_image = FileField(
        "Cover image (optional)",
        validators=[Optional()],
        description="JPEG, PNG, GIF, or WebP; max 2 MB by default.",
    )
    submit = SubmitField("Publish skill post")
