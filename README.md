Self contained Subsurface website code, content, and translations

This code runs on the cloud server to create the Subsurface website.

When working on the content, you can run this locally using

`python3 -m src.web.server -e /tmp/p.data`

The `-e /tmp/p.data` sets a different path for the persistent data since on
your system the default path of `/web/persistent.store` likely doesn't exist.

Make sure that you also create a venv with the required dependencies, first.

Translations are handled on [Transifex](https://app.transifex.com/subsurface/new-website/languages/)
