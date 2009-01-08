#!/bin/sh
cd ..
rsync -a --exclude '.git' .* ~/
