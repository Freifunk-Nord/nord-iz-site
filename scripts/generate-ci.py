#!/usr/bin/python3

import yaml
import subprocess
import os
import copy


ARTIFACTS_EXPIRE = "3 day"
DOCKER_IMAGE = "registry.chaotikum.net/freifunk-luebeck/gluon-build:latest"
QUICK_BUILD_TARGETS = ["ath79-generic", "x86-64", "ramips-mt7620"]
MAKE_FLAGS = ["--silent", "-C", "gluon", "GLUON_SITEDIR=.."]


BEFORE_SCRIPT = [
	"apt-get update > /dev/null",
	"apt-get install -y curl git libncurses-dev build-essential make gawk unzip wget python2.7 file tar bzip2 tree ccache ecdsautils rsync > /dev/null",
	"mkdir -p ccache",
	"mkdir -p logs",
	'PATH="/usr/lib/ccache:$PATH"',
	'git -C gluon fetch --tags',
]

VARIABLES = {
	"GIT_SUBMODULE_STRATEGY": "recursive",
	"CCACHE_DIR": "$CI_PROJECT_DIR/ccache",
	"CCACHE_BASEDIR": "$CI_PROJECT_DIR/ccache",
	"CCACHE_MAXSIZE": "5G",
	"CCACHE_COMPILERCHECK": "content",
	"FORCE_UNSAFE_CONFIGURE": "1",
}


def get_available_targets():
	res = subprocess.run(
		["make", *MAKE_FLAGS, "list-targets"], stdout=subprocess.PIPE)
	if res.returncode != 0:
		print("failed to get gluon targets")
		exit(1)
	return res.stdout.decode('utf-8').strip().split("\n")


# the main ci config
ci = {
	"image": DOCKER_IMAGE,
	"default": {
		"interruptible": True
	},
	"before_script": BEFORE_SCRIPT,
	"workflow": {
		"rules": [
			{'if': '$CI_PIPELINE_SOURCE == "merge_request_event"'},
			{'if': '$CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS', 'when': 'never'},
			{'if': '$CI_COMMIT_BRANCH'}
		]
	},
	"variables": VARIABLES,
	"stages": [
		"pre-build-tests",
		"build",
		"build-on-failure",
		"post build",
		"test",
		"prepare-deploy",
		"test-deploy",
		"deploy",
	]
}

build_all_job = {
	"stage": "build",
	"needs": [],
	"retry": {
		"max": 2,
		"when": "runner_system_failure"
	},
	"cache": {
		"paths": ['ccache']
	},
	"parallel": {
		"matrix": []
	},
	"variables": {
		"GLUON_SITEDIR": "..",
		"GLUON_DEPRECATED": 1,
		"GLUON_AUTOUPDATER_ENABLED": 1,
		"GLUON_AUTOUPDATER_BRANCH": "stable",
		**VARIABLES,
	},
	"script": [
		"file $(which gcc)",
		"du -sh ccache/",
		"ccache -s",
		"ccache -z",
		"tree -L 2",
		"env | grep CI",
		"make -C gluon update",
		'make -C gluon -j $(nproc) GLUON_TARGET=$TARGET 2>&1 | tee "logs/build_${TARGET}.log"',
		"ccache -s"
	],
	"artifacts": {
		# don't add "when: always".
		# it will always skip the build-on-failure stage
		"expire_in": ARTIFACTS_EXPIRE,
		"paths": [
			"gluon/output",
			"logs"
		]
	}
}

ci[".build_all"] = build_all_job

ci['build-all'] = {
	"extends": ".build_all",
	"parallel": {
		"matrix": [{
			"TARGET": get_available_targets(),
		}]
	},
	"rules": [
		{"if": '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'},
		# {'if': '$CI_PIPELINE_SOURCE != "merge_request_event"'},
		# {'if': '$CI_COMMIT_TAG'},
		# {
		# 	'if': '$CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS',
		# 	'when': 'never'
		# },
		# {'if': '$CI_COMMIT_BRANCH'}
	]
}

ci['build-all-quick'] = {
	"extends": ".build_all",
	"parallel": {
		"matrix": [{
			"TARGET": QUICK_BUILD_TARGETS,
		}]
	},
	"rules": [
		{"if": '$CI_COMMIT_BRANCH != $CI_DEFAULT_BRANCH'},
	]
}


# ci['foo'] = dict()
# ci['foo']['stage'] = "build-on-failure"
# ci['foo']['when'] = "on_failure"
# ci['foo']['script'] = ["true"]

# build again if pipeline failed but with verbose flags
ci['build-all-verbose'] = copy.deepcopy(build_all_job)
del ci['build-all-verbose']['needs']

ci["build-all-verbose"]["parallel"]["matrix"] = [{"TARGET": get_available_targets()}]
ci['build-all-verbose']['when'] = "on_failure"
ci['build-all-verbose']['stage'] = "build-on-failure"
ci['build-all-verbose']['dependencies'] = []

# only save logs as artifacts
ci['build-all-verbose']['artifacts']['paths'] = ["logs"]
ci['build-all-verbose']['script'] = [
	"file $(which gcc)",
	"tree -L 3",
	"env | grep CI",
	"make -C gluon update",
	"ccache -s",
	"ccache -z",
	'make -C gluon -j 1 V=sc GLUON_TARGET=$TARGET 2>&1 | tee "logs/build_${TARGET}.log" | tail -c 100000',
	"ccache -s"
]


# test image names
ci['test:images'] = {
	"stage": "test",
	"allow_failure": True,
	"before_script": [],
	"script": [
		# these are the most used devices in luebeck
		"ls gluon/output/images/sysupgrade/ | grep wdr3600",
		"ls gluon/output/images/sysupgrade/ | grep ubiquiti-unifi",
		"ls gluon/output/images/sysupgrade/ | grep wr1043n",
		"ls gluon/output/images/sysupgrade/ | grep avm-fritz-box-4040",
		"ls gluon/output/images/sysupgrade/ | grep x86-64",
		"ls gluon/output/images/sysupgrade/ | grep x86-generic",
		"ls gluon/output/images/sysupgrade/ | grep wdr4300",
		"ls gluon/output/images/sysupgrade/ | grep tp-link-cpe210",
		"ls gluon/output/images/sysupgrade/ | grep ubiquiti-unifi-ac-mesh",
		# these are a few more devices of interest
		"ls gluon/output/images/sysupgrade/ | grep d-link-dap-x1860-a1",
		"ls gluon/output/images/sysupgrade/ | grep eap225-outdoor-v1",
		"ls gluon/output/images/sysupgrade/ | grep gl.inet-gl-usb150",
		"ls gluon/output/images/sysupgrade/ | grep nanostation-loco-m-xw",
		"ls gluon/output/images/sysupgrade/ | grep nanostation-m-xw",
		"ls gluon/output/images/sysupgrade/ | grep plasma-cloud-pa2200",
	]
}

ci['test:image-names'] = {
	"stage": "test",
	"allow_failure": False,
	"before_script": [],
	"script": [
		# check if the image name is valid
		"scripts/ci/test_image_names.sh gluon/output/images/sysupgrade"
	]
}


ci['generate manifest'] = {
	"stage": "post build",
	"cache": {
		"paths": ['ccache']
	},
	"script": [
		"ccache -s",
		"ccache -z",
		"make -C gluon GLUON_SITEDIR=.. update",
		"make -C gluon GLUON_SITEDIR=.. GLUON_PRIORITY=7 GLUON_AUTOUPDATER_BRANCH=stable GLUON_BRANCH=stable manifest",
		"make -C gluon GLUON_SITEDIR=.. GLUON_PRIORITY=0 GLUON_AUTOUPDATER_BRANCH=beta GLUON_BRANCH=beta manifest",
		"make -C gluon GLUON_SITEDIR=.. GLUON_PRIORITY=0 GLUON_AUTOUPDATER_BRANCH=experimental GLUON_BRANCH=experimental manifest",
		"ccache -s"
	],
	"artifacts": {
		"when": "always",
		"expire_in": ARTIFACTS_EXPIRE,
		"paths": [
			"gluon/output"
		]
	}
}


ci['sign manifest'] = {
	"stage": "prepare-deploy",
	"needs": [
		{
			"job": "generate manifest",
   			"artifacts": True
		}
	],
	"rules": [
		{'if': '$SIGNING_KEY'}
	],
	"script": [
		"echo $SIGNING_KEY > ecdsa.key",
		"./gluon/contrib/sign.sh ecdsa.key gluon/output/images/sysupgrade/experimental.manifest",
	],
	"artifacts": {
		"when": "always",
		"expire_in": ARTIFACTS_EXPIRE,
		"paths": [
			"gluon/output/images/sysupgrade/*.manifest",
		]
	}
}


ci['test:manifest-length'] = {
	"stage": "test-deploy",
	"needs": [
		{
			"job": "generate manifest",
   			"artifacts": True
		}
   ],
    "allow_failure": True,
	"before_script": [],
	"script": [
		# check the number of images
		"bash scripts/ci/test_manifest_length.sh"
	]
}

ci['test:manifest-signature'] = {
	"stage": "test-deploy",
	"rules": [
		{'if': '$SIGNING_KEY'}
	],
	"before_script": [],
	"script": [
		# check the number of images
		"PUBKEY=$(echo $SIGNING_KEY | ecdsakeygen -p)",
		"./gluon/contrib/sigtest.sh $PUBKEY gluon/output/images/sysupgrade/experimental.manifest",
	]
}


# Upload Jobs
##############

ci['upload'] = {
	"stage": "deploy",
	"rules": [
		{'if': '$DEPLOY_USER && $DEPLOY_HOST'}
	],
	"before_script": [
		"apt-get -qq update",
		"apt-get -qq install -y git make gawk wget python2.7 file tar bzip2 rsync tree",
		"mkdir -p ~/.ssh",
		'echo -e "StrictHostKeyChecking no" > ~/.ssh/config',
		"eval $(ssh-agent -s)",
		'echo "$DEPLOY_KEY" | ssh-add -',
	],
	"script": [
		"tree -L 3 gluon/output",
		"TAG=$([[ $CI_COMMIT_TAG ]] && echo $CI_COMMIT_TAG || echo $CI_COMMIT_BRANCH)_$(date +%F_%H-%M-%S)",
		'mkdir -p "public/$TAG"',
		"cd gluon",
		"mv output $TAG",
		'ln -s ./$TAG ./latest',
		'rsync -rvhl ./$TAG ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_DIR}/',
		'rsync -rvhl ./latest ${DEPLOY_USER}@${DEPLOY_HOST}:${DEPLOY_DIR}/',
	],
}

ci['upload-package-registry'] = {
	'stage': "deploy",
	'script': [
		"TAG=$([[ $CI_COMMIT_TAG ]] && echo $CI_COMMIT_TAG || echo $CI_COMMIT_BRANCH)_$(date +%F_%H-%M-%S)",
		"tree -L 3",
		'tar -cvzf firmware.tar.gz gluon/output',
		'curl --header "JOB-TOKEN: $CI_JOB_TOKEN" --upload-file firmware.tar.gz "${CI_API_V4_URL}/projects/${CI_PROJECT_ID}/packages/generic/ffhl-firmware/$TAG/ffhl-firmware.tar.gz"',
	],
	'rules': [{
		'if': '$GITLAB_CI'
	}]
}


print(yaml.dump(ci, sort_keys=False,))
# print(get_available_targets())
