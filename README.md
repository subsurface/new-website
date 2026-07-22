# Subsurface Website

This repository contains the code, content, and translations for the
[Subsurface website](https://subsurface-divelog.org/).

## Contributing

Content, design, and code contributions are welcome. Website translations use
a separate workflow; see [Translations](#translations) below.

The usual GitHub workflow is to fork this repository, clone your fork, and
configure the main repository as the `upstream` remote. Replace
`YOUR-USERNAME` with your GitHub username:

```shell
git clone https://github.com/YOUR-USERNAME/new-website.git
cd new-website
git remote add upstream https://github.com/subsurface/new-website.git
```

Create a descriptively named topic branch from the latest upstream code:

```shell
git fetch upstream
git switch -c improve-short-description upstream/main
```

After making and testing the change, stage the relevant files and create a
signed-off commit:

```shell
git status
git diff
git add path/to/changed-file
git commit -s
git push -u origin improve-short-description
```

Then open a pull request against `subsurface/new-website`. The sign-off added
by `git commit -s` certifies the contribution under the
[Developer Certificate of Origin](https://developercertificate.org/).

## Running the Website Locally

Install Docker with the Docker Compose plugin, then run the following command
from the repository root:

```shell
docker compose up --build
```

The local website is available at <http://localhost:8001>. Stop it with
<kbd>Ctrl</kbd>+<kbd>C</kbd>; use `docker compose down` to remove the created
containers.

Release version information in the local instance may be out of date because
production updates it through webhooks that a development instance does not
receive.

## Repository Layout

- `src/web/server.py` contains the main server application.
- `src/web/templates/` contains the page templates and most website content.
- `src/web/static/` contains static assets.
- `docker-compose.yaml` defines the local web and Redis services.

## Translations

Strings in Jinja templates must be marked for translation with
`{{ _("...") }}`. After adding or changing translatable strings, refresh the
translation source catalogue from `src/web`:

```shell
cd src/web
./message-handling.sh extract
```

Include the resulting `messages.pot` update in the same pull request as the
source change. Do not directly edit or submit pull requests for translated
`.po` files. Website translations are managed in the
[Subsurface website project on Transifex](https://app.transifex.com/subsurface/new-website/languages/).

The other `message-handling.sh` commands are intended for maintainers who
synchronize or compile translations; they are summarized in
[`src/web/README.md`](src/web/README.md).
