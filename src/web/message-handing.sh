#!/bin/bash

# super cheesy way to make sure that I don't forget how to deal with the translations
cd $(dirname -- "$(readlink -f "${BASH_SOURCE[0]}")")

while [[ $# > 0 ]] ; do
    case "$1" in
    init)
        if [[ "$2" != "" ]]; then
            if [[ -d translations/"$2" ]] ; then
                echo "we already have a translations/$2 directory... if you really want to init, do it manually"
                exit 1
            fi
            pybabel init -i messages.pot -d translations -l "$2"
            shift
        else
            echo "init needs the language designation as argument"
            exit 1
        fi
        ;;
    update)
        if [[ "$2" != "" ]]; then
            pybabel update -i messages.pot -d translations -l "$2"
            shift
        else
            (
                cd translations
                for t in $(find . -maxdepth 1 -type d -name ??\*); do
			l=$(cut -c3- <<<$t)
			echo $l
			echo "pybabel update -i messages.pot -d translations -l $l"
			(cd .. ; pybabel update -i messages.pot -d translations -l "$l")
                done
            )
        fi
        ;;
    compile)
        pybabel compile -d translations
        ;;
    extract)
        pybabel extract -F babel.config -o messages.pot .
    esac
    shift
done
