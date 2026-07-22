# Translation Maintenance

General contribution and local-development instructions are in the
[repository README](../../README.md#contributing).

Run `message-handling.sh` from this directory to maintain the website's Babel
translation catalogues:

```shell
./message-handling.sh extract          # Regenerate messages.pot
./message-handling.sh update           # Update every existing PO catalogue
./message-handling.sh update LANGUAGE  # Update one PO catalogue
./message-handling.sh init LANGUAGE    # Initialize a new PO catalogue
./message-handling.sh compile          # Compile PO catalogues for local use
```

Contributors changing translatable source strings normally need only the
`extract` command and should commit the resulting `messages.pot` change.
Translated `.po` files are synchronized through the
[Subsurface website project on Transifex](https://app.transifex.com/subsurface/new-website/languages/)
and should not be edited in pull requests.
