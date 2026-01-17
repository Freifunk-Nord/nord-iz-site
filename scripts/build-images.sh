#!/bin/bash
set -ex

export GLUON_RELEASE="2020.2.3-4"
export FORCE_UNSAFE_CONFIGURE=1
export GLUON_SITEDIR=..
export GLUON_AUTOUPDATER_ENABLED=1
export GLUON_DEPRECATED=full

if [ -z "$GLUON_TARGET" ]; then
	TARGETS="ath79-generic x86-64 ramips-mt7620"
else
	TARGETS="$GLUON_TARGET"
fi

THREADS=$(($(nproc)+1))

FLAGS="-j 1 V=sc"
# FLAGS="-j $THREADS"

make -C gluon update

for target in $TARGETS; do
	echo "=================================================="
	echo ""
	echo "$FLAGS" GLUON_TARGET="$target"
	make -C gluon $FLAGS GLUON_TARGET="$target"
done

exit
