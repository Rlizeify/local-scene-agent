# Installation

## Requirements
- Python 3.10+
- Claude Code (CLI, desktop app or IDE extension) or another Claude client that supports personal skills in `~/.claude/skills`
- Optional, for better research: web search, a browser tool (built-in browser or Claude in Chrome), a Notion or Google Docs connector if your scene guide lives there, push notifications (Claude desktop/mobile app), scheduled tasks (Claude desktop app) or routines (claude.ai)

## Steps
```bash
git clone https://github.com/<you>/local-scene-agent.git
cd local-scene-agent
python -m pip install -e .          # or: pip install -r requirements.txt and call python lsa.py
python lsa.py skill install-onboarding
```

Then in Claude, type **`/local-scene-setup`**. The interview takes 10–15 minutes; point it at any guide or list you already keep. At the end you approve your profile and it installs **`/local-scene`**.

## Where things live
| What | Where | Override |
|---|---|---|
| Engine (this repo) | your clone | `LSA_ENGINE_ROOT` |
| Your data | `~/.local-scene-agent/users/<id>/` | `LSA_HOME` or `--home` |
| Skills | `~/.claude/skills/` | `LSA_SKILLS_DIR` |
| Default user | the only one, else `--user` | `LSA_USER` |

No API keys or secrets are needed. Connectors (Notion, Gmail, calendar) are authorized in your Claude app, never stored here.

## Updating
```bash
git pull
python lsa.py skill install-onboarding
python lsa.py --user <id> skill install --force
```
Your profile and log are untouched. If `schema_version` changes, CHANGELOG.md says how to migrate.

## Uninstalling
```bash
python lsa.py skill uninstall --name local-scene
python lsa.py skill uninstall --name local-scene-setup
```
Then delete `~/.local-scene-agent` if you want your data gone too. The uninstaller refuses to remove skills it didn't create.
