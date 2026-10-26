# GitHub handoff

Synthetic data. The final report is `powerbi/Wallet.pbip`; keep both adjacent
`Wallet.Report` and `Wallet.SemanticModel` directories. Their JSON/TMDL files
are necessary source files, not disposable clutter.

Git includes README, requirements, source, tests, SQL, final PBIP definitions,
documentation and small aggregate validation snapshots. It excludes `.venv`,
raw generated data, `.pbi` caches/settings, binary PBIX files and backups.

Earlier report copies and milestone notes remain locally because this session's
automatic approval review rejected filesystem deletion. They are explicitly
excluded from Git. If desired, delete these superseded items manually:

- Root `Wallet.Report`, `Wallet.SemanticModel`, `Wallet.pbip`
- `WalletProfessional`
- `powerbi/before_model_setup`, `powerbi/model_after_setup`, `powerbi/powerbi`
- `docs/milestone_1_results.md`, `docs/milestone_2_loading.md`,
  `docs/power_bi_first_import.md`, `docs/power_bi_model_setup_results.md`
- `data/repeat`, `data/final_model_export` and Python `__pycache__` folders

Keep `powerbi/Wallet.Report`, `powerbi/Wallet.SemanticModel` and
`powerbi/Wallet.pbip`. The local `.venv` and `data/synthetic` are useful for reruns
and already excluded from Git.

Before publishing, review the exact file list:

```powershell
git status --short
git ls-files --others --exclude-standard
```

Create an empty GitHub repository, then run from this folder:

```powershell
git add .
git diff --cached --stat
git commit -m "Add synthetic digital wallet BI portfolio"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/digital-wallet-bi.git
git push -u origin main
```

Replace YOUR_USERNAME. No remote, commit or publication was performed automatically.
Use Git rather than uploading the entire local folder, so exclusions are respected.
