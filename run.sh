#!/bin/bash
#
# Example script for the m4e tools
#
# To use it, download a couple of files from Eclipse and put them into "downloads"

cd src
for f in ../downloads/* ; do
    ./m4e-import.py "$f" || exit 1
done

folders=
for d in ../tmp/*_home/m2repo ; do
    if [[ "$d" = */priming_home/* ]]; then
    	continue
    fi
    folders="$folders '$d'"
done

if [[ -d ../tmp/m2repo ]]; then
    rm -r ../tmp/m2repo
fi
eval ./m4e-merge.py $folders ../tmp/m2repo || exit 1
./m4e-attach-sources.py ../tmp/m2repo || exit 1
./m4e-apply-patches.py ../patches ../tmp/m2repo || exit 1
./m4e-analyze.py ../tmp/m2repo || exit 1
./m4e-dm.py ../tmp/m2repo org.eclipse.m4e:m4e-dependencyManagement:3.6.2 || exit 1

exit 0
