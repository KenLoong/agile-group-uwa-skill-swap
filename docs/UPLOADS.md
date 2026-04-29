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

## Future implementation notes

When full Flask upload handling is connected, the route should save post images under this directory or under a configured equivalent path.

Future upload implementation should also include:

- allowed extension checks;
- MIME/content validation;
- file size limits;
- safe generated filenames;
- error messages for invalid uploads;
- tests for accepted and rejected files.

This policy only defines repository tracking rules. It does not implement upload validation or file storage logic.