# Claude Skills

A collection of [Claude Code](https://claude.com/claude-code) plugins by [@rahulmg05](https://github.com/rahulmg05).
Each plugin adds one or more skills. Claude uses a skill when your request matches it, or when you type its slash command.

## Plugins

| Plugin | Description |
|---|---|
| [task-tracker](task-tracker/) | Track personal tasks from the terminal. Move tasks through Not Started, In Progress, Blocked, and Done, list them by status or period, and view a read-only board. |

## Installation

1. Start Claude Code.
2. Add this repository as a plugin marketplace:
   ```
   /plugin marketplace add rahulmg05/claude-skills
   ```
3. Install a plugin:
   ```
   /plugin install task-tracker@claude-skills
   ```
4. Restart Claude Code to load the plugin.

To get updates later, run `/plugin marketplace update claude-skills`.

## Repository layout

```
claude-skills/
├── .claude-plugin/
│   └── marketplace.json      # the list of plugins in this marketplace
└── <plugin>/
    ├── .claude-plugin/
    │   └── plugin.json       # plugin name, version, author
    └── skills/
        └── <skill>/
            └── SKILL.md      # the instructions Claude follows
```

## License

Public domain, under [The Unlicense](LICENSE). You can use this code for any purpose, with no conditions.
