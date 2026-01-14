#!/bin/bash
set -u
set -e

# if version is unset, will use the default version from site.mk
#VERSION=${3:-"2018.2.1~exp$(date '+%y%m%d%H%M')"}
VERSION=${3:-"2018.2.1"}
# branch must be set to either rc, nightly or stable
BRANCH=${2:-"stable"}

# BROKEN must be set to "" or "BROKEN=1"
BROKEN="BROKEN=1"

# set num cores +1
#CORES="-j$(nproc)"
CORES="-j1"

# set this to "0" if you don't want to use make clean before make
MAKE_CLEAN="0"

# set this to "" to get less more output
VERBOSE="V=sc"
#VERBOSE=""

#ONLY_TARGET must be set to "" or i.e. "ar71xx-tiny"
#ONLY_TARGET=""
ONLY_TARGET="ar71xx-generic"
#to build only one device set DEVICES list (only if $ONLY_TARGET!="")
#DEVICES=''
DEVICES='DEVICES=tp-link-tl-wr842n-nd-v3'

cd gluon

echo "############## starting build process #################"
sleep 3

#rm -r output

#  ramips-mt7621:  BROKEN: No AP+IBSS support, 11s has high packet loss
#  ramips-rt305x:  BROKEN: No AP+IBSS support

WRT1200AC="mvebu" # Linksys WRT1200AC BROKEN: No AP+IBSS+mesh support

ONLY_11S="ramips-rt305x ramips-mt7621"    # BROKEN only

ONLY_LEDE="ar71xx-tiny" # Support for for 841 on lede, needs less packages, so the 4MB will suffice!
ONLY_LEDE+=" x86-geode ipq806x ramips-mt76x8"
NOT_LEDE="x86-kvm_guest" # The x86-kvm_guest target has been dropped from LEDE; x86-64 should be used

BANANAPI="sunxi-cortexa7"                          # BROKEN: Untested, no sysupgrade support
MICROTIK="ar71xx-mikrotik"                # BROKEN: no sysupgrade support

RASPBPI="brcm2708-bcm2708 brcm2708-bcm2709"
X86="x86-64 x86-generic x86-xen_domu"
WDR4900="mpc85xx-generic"

TARGETS="ar71xx-generic $ONLY_LEDE ar71xx-nand $WDR4900 $RASPBPI $X86"
if [ "$BROKEN" != "" ]; then
  TARGETS+=" $BANANAPI $MICROTIK $WRT1200AC"
fi

if [ "$ONLY_TARGET" != "" ]; then
  TARGETS="$ONLY_TARGET"
fi

for TARGET in $TARGETS; do
  OPTIONS="GLUON_SITEDIR=.. GLUON_TARGET=$TARGET $BROKEN $CORES GLUON_BRANCH=$BRANCH GLUON_RELEASE=$VERSION"
  make $OPTIONS update

  if [ $MAKE_CLEAN = 1 ]; then
    echo -e "\n===========\n\n\n\n\nmake $OPTIONS clean"
    make $OPTIONS clean
  fi
  make $OPTIONS $DEVICES $VERBOSE
done


MANIFEST_OPTINS="GLUON_RELEASE=$VERSION $BROKEN $CORES"
if [[ true ]]; then
  B="nightly"
  make $MANIFEST_OPTINS GLUON_BRANCH=$B manifest
fi

if [[ "$BRANCH" == "stable" ]]; then
  B="stable"
  make $MANIFEST_OPTINS GLUON_BRANCH=$B manifest
fi

echo "Done :)"
