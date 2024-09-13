#!/bin/bash

# set things up for a current release
#
# this doesn't include (of course) the signing of the Windows and macOS installers
# also - you'll need to restart the docker container for the website afterwards

croak() {
    echo "$*" ; exit 1
}

cd $(dirname -- "$(readlink -f "${BASH_SOURCE[0]}")") || croak "can't cd to script dir"

STATICPATH=/data/www/subsurfacestaticsite/downloads

[[ $1 == "" ]] && croak "Usage: ${BASH_SOURCE[0]} buildnr"

BUILDNR="$1"
TODAY=$(date +%Y-%m-%d)

[[ ! -f "$STATICPATH"/Subsurface-6.0.${BUILDNR}-CICD-release.dmg ]] && croak "missing the signed dmg in downloads"

sed -i '/^crelease/d' persistent.store
echo "crelease=\"6.0.$BUILDNR\"" >> persistent.store
echo "crelease_date=\"$TODAY\"" >> persistent.store

cd $STATICPATH || croak "can't cd to $STATICPATH"
for f in subsurface-6.0.${BUILDNR}-CICD-release-installer.exe \
        Subsurface-mobile-6.0.${BUILDNR}-CICD-release.apk \
        Subsurface-6.0.${BUILDNR}-CICD-release.AppImage
do
    wget "https://github.com/subsurface/nightly-builds/releases/download/v6.0.${BUILDNR}-CICD-release/$f"
done
