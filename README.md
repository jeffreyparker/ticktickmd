# TickTick to Markdown Converter

A Python tool to convert TickTick tasks into structured markdown files, preserving your tasks, notes, and checklists in a format compatible with popular note-taking apps like Obsidian, Logseq, and Notion.

Supports both **CSV backup exports** and the **TickTick Open API** for pulling tasks directly.

(Note, this was coded primarily with Claude Code. It's working fine for my needs, but there may be rough edges.)

## Features

- **CSV Import**: Convert TickTick CSV backup exports
- **API Import**: Pull tasks directly from TickTick via the Open API
- **Hierarchical Structure**: Organizes tasks as `Folder/List/Task.md`
- **YAML Frontmatter**: Preserves all metadata (dates, priority, status, tags)
- **Checklist Support**: Converts TickTick checkbox format to standard markdown `- [ ]` / `- [x]`
- **Subtasks**: Automatically includes subtasks within parent task files
- **List Indexes**: Generates index files with wikilinks for easy navigation
- **Multiple Output Modes**: Hierarchical, flat, or single-file output

## Requirements

- [uv](https://github.com/astral-sh/uv) (recommended) or standard Python

## Usage

The tool has two modes: **csv** for importing from backup files, and **api** for pulling directly from TickTick.

### From CSV Backup

#### Exporting from TickTick

1. Open TickTick on web or desktop
2. Go to Settings → Backup
3. Click "Export data as CSV"
4. Save the CSV file

#### Converting

```bash
# Using uvx (recommended - no installation needed)
uvx ticktickmd csv backup.csv -o output/

# Or if installed locally
ticktickmd csv backup.csv -o output/
```

### From TickTick API

#### Setup

1. Create a TickTick API app at https://developer.ticktick.com/manage
2. Set the OAuth redirect URL to `http://localhost:8090/callback`
3. Run the auth setup:

```bash
uvx ticktickmd auth login
```

This will prompt for your Client ID and Client Secret, then open a browser to authorize the app.

#### Pulling Tasks

```bash
# Fetch all tasks
uvx ticktickmd api -o output/

# Fetch only a specific project
uvx ticktickmd api -o output/ --project "Work"
```

#### Managing Auth

```bash
# Check auth status
ticktickmd auth status

# Log out (clear stored tokens)
ticktickmd auth logout
```

### Output Options

These options work with both `csv` and `api` commands:

```bash
# Include archived/completed tasks (excluded by default)
uvx ticktickmd csv backup.csv -o output/ --include-archived

# Flat structure (all files in one directory)
uvx ticktickmd csv backup.csv -o output/ --flat

# Single combined markdown file
uvx ticktickmd csv backup.csv -o all_tasks.md --single-file

# Don't generate list index files
uvx ticktickmd csv backup.csv -o output/ --no-index

# Verbose output
uvx ticktickmd csv backup.csv -o output/ -v
```

This creates a hierarchical directory structure:

```
output/
├── Work/
│   ├── Projects/
│   │   ├── _index.md
│   │   ├── Task 1.md
│   │   └── Task 2.md
│   └── Meetings/
│       └── ...
└── Personal/
    └── ...
```

## Output Format

Each task becomes a markdown file with YAML frontmatter:

```markdown
---
title: "Buy groceries"
folder: "Personal"
list: "Shopping"
kind: "CHECKLIST"
tags: [errands, weekly]
status: "active"
priority: "high"
created: 2025-01-15T10:30:00+00:00
due: 2025-01-20
timezone: "America/New_York"
ticktick_id: "12345"
---

# Buy groceries

- [ ] Milk
- [ ] Eggs
- [x] Bread
- [ ] Coffee

---
Due: 2025-01-20 | Priority: high | Tags: errands, weekly
```

### Task Types

- **TEXT**: Simple text tasks
- **NOTE**: Longer notes with content
- **CHECKLIST**: Tasks with checkbox items

### Status Values

- **active**: Normal, incomplete task (Status = 0)
- **completed**: Completed task (Status = 1)
- **archived**: Archived task (Status = 2)

Note: Archived tasks are excluded by default. Use `--include-archived` to include them.

## Known Limitations

### 1. Attachments/Images Not Included

**The CSV export does not contain attachment URLs or image data.** TickTick only exports text content, metadata, and task structure. Attachments would need to be:
- Manually downloaded from TickTick before exporting
- Downloaded via TickTick API (requires OAuth authentication setup)

If attachment preservation is critical, consider:
- Downloading attachments manually from the app before export
- Using TickTick's built-in backup feature (may include attachments)
- Implementing API-based download (would require significant additional work)

### 2. Formatting Variations

TickTick concatenates list items without newlines in the CSV export. This tool attempts to split them intelligently, but complex formatting may not be perfectly preserved:

- Multiple consecutive dashes may be split incorrectly
- Code blocks within notes are preserved but not syntax-highlighted
- Tables are not specially handled

### 3. Recurring Tasks

Recurring task definitions are preserved in the `repeat` field (e.g., `RRULE:FREQ=DAILY`), but only completed instances are exported. Future occurrences are not included.

### 4. Comments/Collaboration

The CSV export does not include:
- Task comments
- Collaboration history
- Activity logs
- Shared list member information (only shows "Shared" tag)

### 5. Custom Fields

TickTick custom fields or properties (if any) may not be exported in the CSV format.

### 6. Timezone Handling

Dates are exported in UTC with timezone information preserved in metadata. Your note-taking app may display them differently based on its timezone handling.

## Compatibility

### Obsidian

Fully compatible! The output works great with:
- Standard markdown rendering
- [Obsidian Tasks](https://github.com/obsidian-tasks-group/obsidian-tasks) plugin
- Wikilinks in index files
- Frontmatter queries

### Logseq

Compatible with standard markdown. For best results:
- Logseq prefers `TODO` / `DONE` keywords
- May need to convert `- [ ]` checkboxes manually or with a script

### Other Apps

The standard markdown format should work with most apps that support:
- YAML frontmatter (optional)
- Standard markdown checkboxes
- File/folder organization

## Tips

### Organizing Output

1. **Use hierarchical structure** (default) for best organization
2. **Generate index files** (default) for easy navigation with wikilinks
3. **Include archived tasks** if you want a complete backup
