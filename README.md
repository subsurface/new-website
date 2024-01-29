Self contained Subsurface website code, content, and translations

This code runs on the cloud server to create the Subsurface website.

When working on the content, you can run this locally.
First create the venv with the required dependencies

```
python3 -m venv venv
source ./venv/bin/activate
pip install -r requirements.txt
```

Now you can start the webserver locally - the first time it runs it will
create its own clone of the Subsurface source repo in order to get the
user manuals, the corresponding pictures, and the list of supported dive
computers from that.

`python3 -m src.web.server`

You can now access your version of the website at `http://localhost:8002`

Of course the version numbers for latest release and current release
will be off (as those get populated through webhooks that your server
won't receive).

The main server app is driven by `src/web/server.py`, the page templates
are in the `src/web/templates` directory.

Strings are marked for translation with `{{ _("...") }}` (as is typical
for Jinja2 templates). There is a script to simplify processing of the
translation strings, but I doubt that this is useful for many people.

The translations themselves are handled on [Transifex](https://app.transifex.com/subsurface/new-website/languages/)
