#!/bin/bash

[[ -d ~/.zgen ]] || git clone https://github.com/tarjoilija/zgen ~/.zgen

./create_symlink.py
