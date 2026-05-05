# Upload Directory Policy

This document describes how the repository handles user-uploaded post images.

## Purpose

Skill posts may include an optional image. Uploaded image files are runtime data, not source code, so they should not be committed to Git.

The repository keeps the expected directory structure with a `.gitkeep` file:

```text
static/uploads/posts/.gitkeep
```

This allows fresh clones to contain the upload directory while still preventing local uploaded files from being tracked.

## Tracked files

The following placeholder is tracked:

```text
static/uploads/posts/.gitkeep
```

This file exists only to keep the upload directory present in Git.

## Ignored files

Runtime uploaded files under the post upload directory are ignored:

```text
static/uploads/posts/*
```

The `.gitignore` file then explicitly allows the placeholder:

```text
!static/uploads/posts/.gitkeep
```

## What should not be committed

Do not commit:

- user-uploaded post images;
- temporary upload test files;
- screenshots copied into the upload directory;
- generated thumbnails or resized upload outputs.

Examples of files that should remain untracked:

```text
static/uploads/posts/example.jpg
static/uploads/posts/demo.png
static/uploads/posts/test-upload.webp
```

## Local verification

To verify that upload files are ignored:

```bash
git check-ignore static/uploads/posts/example.jpg
```

This should print the ignored path.

To verify that the placeholder is still trackable:

```bash
git check-ignore static/uploads/posts/.gitkeep
```

This should produce no output.

## Application behaviour

The create-post flow accepts an optional **cover image** on `POST /posts/create` using **`multipart/form-data`**. The backend:

- Validates **content** via **magic bytes** (JPEG, PNG, GIF, WebP).
- Enforces **`MAX_POST_IMAGE_BYTES`** (default **2 MiB**, set in `app.py`).
- Writes files under **`static/uploads/posts/`**, or under **`POST_COVER_UPLOAD_DIR`** when set (unit tests point this at a temp directory).
- Persists only a **basename** on `Post.image_filename`, using a high-entropy hex name and correct extension — client-provided names are not used on disk.
- Authors may supply optional **`Post.image_alt`** (max 200 characters) when uploading a cover; it is surfaced in HTML `alt`, `GET /posts/<id>/json`, and discover `GET /api/filter` cards as **`image_alt`**.

Implementation: **`api/post_cover_upload.py`** · form fields: **`CreatePostForm.cover_image`**, **`CreatePostForm.image_alt`**.