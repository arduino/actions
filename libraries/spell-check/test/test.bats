#!/usr/bin/env bats

# Tests using the Bats testing framework

@test "Find misspelled words" {
  # codespell's exit status is the number of misspelled words found
  expectedExitStatus=6
  run ./entrypoint.sh
  echo "Exit status: $status | Expected: $expectedExitStatus"
  [ $status -eq $expectedExitStatus ]
}

@test "Use ignore-words-list argument" {
  expectedExitStatus=0
  run ./entrypoint.sh "./test/testdata/codespell-ignore-words-list.txt"
  echo "Exit status: $status | Expected: $expectedExitStatus"
  [ $status -eq $expectedExitStatus ]
}

@test "Ignore .git" {
  expectedExitStatus=6
  mkdir ".git"
  cp "./test/testdata/has-misspellings/has-misspellings1/has-misspellings.txt" "./.git"
  run ./entrypoint.sh
  rm  --recursive "./.git"
  echo "Exit status: $status | Expected: $expectedExitStatus"
  [ $status -eq $expectedExitStatus ]
}

@test "Skip wildcard path" {
  expectedExitStatus=2
  run ./entrypoint.sh "" "./test/testdata/has-misspellings/has-misspellings*"
  echo "Exit status: $status | Expected: $expectedExitStatus"
  [ $status -eq $expectedExitStatus ]
}

@test "Skip paths" {
  expectedExitStatus=2
  run ./entrypoint.sh "" "./test/testdata/has-misspellings/has-misspellings1","./test/testdata/has-misspellings/has-misspellings2"
  echo "Exit status: $status | Expected: $expectedExitStatus"
  [ $status -eq $expectedExitStatus ]
}
