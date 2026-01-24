# TickTick to Markdown Converter

A Python tool to convert TickTick CSV backup exports into structured markdown files, preserving your tasks, notes, and checklists in a format compatible with popular note-taking apps like Obsidian, Logseq, and Notion.

## Features

- **Hierarchical Structure**: Organizes tasks as `Folder/List/Task.md`
- **YAML Frontmatter**: Preserves all metadata (dates, priority, status, tags)
- **Checklist Support**: Converts TickTick checkbox format to standard markdown `- [ ]` / `- [x]`
- **Subtasks**: Automatically includes subtasks within parent task files
- **List Indexes**: Generates index files with wikilinks for easy navigation
- **Multiple Output Modes**: Hierarchical, flat, or single-file output

## Requirements

- Python 3.9 or higher
- [uv](https://github.com/astral-sh/uv) (recommended) or standard Python

No external dependencies required - uses only Python standard library.

## Installation

### Quick Start (Recommended)

If you have [uv](https://github.com/astral-sh/uv) installed, you can run this tool directly without installation:

```bash
uvx ticktickmd backup.csv -o output/
```

This will automatically download and run the latest version.

### Manual Installation

1. Clone or download this repository
2. Ensure you have Python 3.9+ installed
3. (Optional) Install with pip: `pip install -e .`

## Usage

### Exporting from TickTick

1. Open TickTick on web or desktop
2. Go to Settings → Backup
3. Click "Export data as CSV"
4. Save the CSV file

### Basic Conversion

```bash
# Using uvx (recommended - no installation needed)
uvx ticktickmd backup.csv -o output/

# Or if installed locally
ticktickmd backup.csv -o output/

# Or using uv run from the repository
uv run ticktickmd backup.csv -o output/

# Or using standard Python from the repository
python -m ticktickmd.cli backup.csv -o output/
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

### Command Line Options

```bash
# Include archived/completed tasks (excluded by default)
uvx ticktickmd backup.csv -o output/ --include-archived

# Flat structure (all files in one directory)
uvx ticktickmd backup.csv -o output/ --flat

# Single combined markdown file
uvx ticktickmd backup.csv -o all_tasks.md --single-file

# Don't generate list index files
uvx ticktickmd backup.csv -o output/ --no-index

# Verbose output
uvx ticktickmd backup.csv -o output/ -v
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

### Notion

Can import the markdown files:
- Frontmatter may not be fully preserved
- Checkboxes work as expected
- Hierarchy is maintained

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

### Migration Workflow

1. Export CSV from TickTick
2. Convert to markdown with this tool
3. Import into your target app
4. Manually download any critical attachments from TickTick
5. Cross-reference against the TickTick app to verify nothing was missed

### Automation

Add to a backup script:

```bash
#!/bin/bash
# Download latest TickTick backup (manual step)
# Then run:
uvx ticktickmd ~/Downloads/TickTick-backup-*.csv -o ~/Notes/TickTick-Archive/ --include-archived
```

## Contributing

Suggestions and improvements welcome! Key areas for enhancement:

- API integration for attachment download
- Alternative output formats (Logseq, Joplin, etc.)
- Better handling of complex content formatting
- Template customization options

## License

Free to use and modify for personal use.
