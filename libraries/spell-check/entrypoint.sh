#!/bin/bash -x

IGNORE_WORDS_LIST=$1

CODE_SPELL_ARGS="--skip=.git"

if test -f "$IGNORE_WORDS_LIST"; then
	CODE_SPELL_ARGS="${CODE_SPELL_ARGS} --ignore-words=${IGNORE_WORDS_LIST}"
fi

codespell ${CODE_SPELL_ARGS} .
