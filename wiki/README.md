# GitHub Wiki source

Markdown in the repository root (`FAQ.md`, `ACKNOWLEDGEMENTS.md`, `CHANGELOG.md`, `README.md`) is the **canonical** documentation.

After editing those files, publish to the GitHub Wiki tab:

```powershell
.\scripts\publish_wiki.ps1
```

Requirements:

- [GitHub CLI](https://cli.github.com/) (`gh auth login`) **or** git push access to `forza-painter-fh6.wiki.git`
- Wiki enabled on the repository (**Settings → Features → Wikis**)

The script copies root docs into the wiki repo as `Home`, `FAQ`, `Acknowledgements`, and `Changelog` pages.
