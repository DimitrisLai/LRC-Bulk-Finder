# v2.9.4 — One-click Greek G2G AI setup for Windows

### Why the checkbox was disabled
The standalone app does not bundle AUEB's 1.2 GB Greeklish-to-Greek model, Python, PyTorch, or other heavy dependencies. In v2.9.3 the GUI protected users from selecting an AI mode that would inevitably fail. v2.9.4 adds a dedicated, optional installer and runtime companion.

### New behavior
- Click **Install / verify Greek G2G AI (one click)** inside Saved searches → Downloads & local setup.
- Read/accept the download confirmation. No command-prompt navigation, manual folders or hand editing of PATH are required.
- When necessary, the installer searches for Python 3.10–3.13 and can use Windows winget to install official Python 3.11. Windows/winget may request separate permissions.
- Creates an isolated environment under Local AppData/LRCBulkFinder/G2G, installs CPU-oriented PyTorch and the upstream `gr-nlp-toolkit==0.3.0`, downloads the full G2G model and runs an actual conversion test.
- A verified marker is written **only after** the self-test succeeds. Then the AI checkbox and Greek Local AI FULL preset become available in the standalone GUI. Failure or interruption keeps the option disabled; dictionary-only Greek search still works.
- A persistent local Python companion handles AI conversions in the search worker without loading the large model repeatedly; inference is CPU-based so modest 4 GB GPUs are not required. Once installed, search-time model loading uses offline HF settings.
- The progress window shows installer output; the app refuses to begin a music search while installing.

### Safety
No installation begins without clicking the button and explicitly approving the network/download notice. No audio files, existing LRCs or ID3 metadata are changed by installation. The AI generates text SEARCH SUGGESTIONS and does not verify song/lyrics matches. A separate user environment avoids altering system-wide Python. Upstream downloads and optional winget/Python setup require internet and disk space and are subject to their own licenses and platforms.

### Limitations and QA
- **The full model is ~1.2 GB plus potentially multiple GB of dependencies** and may use substantial CPU/RAM. It is not included in the ZIP.
- Windows PowerShell/winget availability and antivirus settings vary; the GUI reports real failures rather than claiming setup success.
- GitHub offline tests mock installers/models and verify readiness/fallback. Frozen-EXE tests validate entrypoints, worker status and packaging. **The first real model download/inference still requires acceptance testing on a user's Windows computer.**
- This is a beta. Existing v2.9.3 Windows release remains intact, and all previous Greek dictionaries, 15 search presets, UTF-8 fixes, STOP protection and no-overwrite logic are retained.
