# Quick Notes

This needs to be scripted / handled by a Makefile

To extract the latest strings use

`pybabel extract -F babel.config -o messages.pot .`

This writes the PO template file to messages.pot

For each language then run

`pybabel update -i messages.pot -d translations -l de`

in order to merge the changes into the translation. All this should then get handled via transifex.

Finally, compile the translations for use

`pybabel compile -d translations`
