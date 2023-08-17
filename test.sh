#!/bin/bash

scripts=$(find . -name "*.py")

for script in $scripts; do
    echo "$script"
    script_dir=$(dirname "$script")
    echo "$script_dir"
    # cd "$script_dir"
    # python "$(basename "$script")"
    # cd -
done