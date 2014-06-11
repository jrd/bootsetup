#!/bin/sh
cd $(dirname "$0")
# create resources/po/bootsetup.pot template file from glade file
xgettext --from-code=utf-8 \
	-L Glade \
	-o resources/po/bootsetup.pot \
	bootsetup/bootsetup.glade
# update resources/po/bootsetup.pot template file from python files
for p in bootsetup/*.py; do
  xgettext --from-code=utf-8 \
    -j \
    -L Python \
    -o resources/po/bootsetup.pot \
    $p
done
# create resources/bootsetup.desktop.in.h containing the key to translate
intltool-extract --type="gettext/ini" resources/bootsetup.desktop.in
# use the .in.h file to update the template file
xgettext --from-code=utf-8 \
  -j \
  -L C \
  -kN_ \
  -o resources/po/bootsetup.pot \
  resources/bootsetup.desktop.in.h
# remove unused .in.h file
rm resources/bootsetup.desktop.in.h
# update the po files using the pot file
(
  cd resources/po
  for p in *.po; do
	  msgmerge -U $p bootsetup.pot
  done
  rm -f ./*~
)
