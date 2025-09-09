# nodepicker 🪄🟢

A tiny interactive helper (or wrapper rather) for ultra-fast Node.js version switching inside **tmux** (or **byobu** using the tmux backend). It wraps your existing **nvm** install and streamlines two high‑frequency actions:

1. Change the Node.js version for the current pane / shell session.
2. Set (and immediately apply) the global *default* Node.js version (`nvm alias default <version>` + `nvm use default`).

> Born out of the annoyance of constantly hopping between legacy and cutting‑edge Node versions during daily work (testing, CI/CD, works on my machine, many many lambdas with different runtimes etc)

---
## ✨ Features
- 🔢 Clean numeric menu of actually installed Node versions (scans `$NVM_DIR/versions/node/*`)
- 🕶 Session switch: sends exactly one `nvm use <version>` command
- 🌍 Default switch: updates alias + applies with `nvm use default`, for subsequent cases add `nvm use default` to your dot shell rc file (.bashrc, .zshrc)
- 🤏 Zero magic beyond automating keystrokes in your active tmux pane
- 🛑 No mutation of your shell config, no background daemons

---
## 📦 Installation (via pipx)
Ensure you have Python 3.9+ and [pipx](https://pypa.github.io/pipx/) installed.

```bash
pipx install nodepicker
# Or from a local clone
pipx install .
```
If you are developing locally and want updates reflected:
```bash
pipx install --force --editable .
```

After install, `nodepicker` should be on your PATH via pipx shims.

---
## ✅ Prerequisites
| Requirement | Why |
|-------------|-----|
| `nvm` installed | Provides Node version management; `nodepicker` only orchestrates it. |
| `NVM_DIR` env var set | Needed to locate installed versions (`~/.nvm` by default). |
| `tmux` (or byobu w/ tmux backend) | Used to inject keystrokes/commands. |
| Installed Node versions via `nvm install <ver>` | Only those with a real `bin/node` are listed. |

> Not supported: plain shells without tmux, other managers (fnm, asdf) — PRs welcome.

---
## 🚀 Usage
Inside an existing tmux pane run:
```bash
nodepicker
```
You will see:
```
--- NVM Node Version Picker ---

Select an action:
1. Change Node version for current session
2. Change default Node version
q. Quit
```

### 1. Current session switch
- Pick a number for the version.
- Tool injects: `nvm use <version>`
- Only affects the current pane (your other panes stay as-is).

### 2. Set default version
- Pick a number.
- Tool injects:
  - `nvm alias default <version>`
  - `nvm use default`
- Your current pane now runs the new default.
- New tmux panes / login shells (that run `nvm use default` in `.zshrc`) will pick it up automatically.

Add this to your `~/.zshrc` (if you haven't already) to ensure consistency:
```bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
nvm use --silent default >/dev/null 2>&1 || true
```

---
## 🧩 How it finds versions
It scans: `$(NVM_DIR)/versions/node/*/bin/node`.
- Only directories with a real `node` binary are considered.
- This avoids listing remote / alias / nonexistent versions that `nvm ls` sometimes prints.

---
## 🔧 Troubleshooting
| Problem | Cause | Fix |
|---------|-------|-----|
| "This script must be run inside a tmux session." | Not in tmux | Start `tmux` first. |
| No versions listed | `NVM_DIR` wrong or empty | Echo `$NVM_DIR`; reinstall or export correct path. |
| Alias changes but new panes use old version | Shell config pins a version | Remove hardcoded `nvm use <ver>`; use `nvm use default`. |
| Command not found: nodepicker | pipx path not in shell | Run `pipx ensurepath` and restart shell. |

Verbose check:
```bash
echo $NVM_DIR
ls $NVM_DIR/versions/node
nvm alias
```

---
## ⚠️ Limitations
- No non-tmux mode.
- No install-on-missing (e.g., auto `nvm install <ver>`).
- No support for alternative managers (asdf/fnm) out of the box.

---
## 🗺 Roadmap (ideas)
- Non-tmux fallback that just prints the command.
- Optional fuzzy search when you have many versions.
- Auto-install missing version on selection.
- Plugin hooks (run a script after switch).

---
## 🤝 Contributing
Lightweight project — feel free to open issues / PRs with clean, minimal changes.

---
## 🙌 Inspiration
Just scratching the personal itch of having to frequently change Node versions, in as few movements as possible, ideally without even retyping versions (yes, that often). I enumerated several cases at the beginning of the file, but since you're already here, I can't really remember the syntax of all the version switchers and it's too much typing, this allows you to just do 'nsw' '1' '7' done- wow! nsw! great alias! use it, typing eats away at seconds of your time and that compounds :D

Enjoy! ⚡
