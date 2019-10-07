#!/bin/bash

docker build -t make_asset_dataset .
docker run -it --rm -v /mnt/raid/research/irates/data/raw/bloomberg:/app/bloomberg \
                    -v /mnt/raid/research/irates/data/processed:/app/output \
                    -u `id -u $USER`:`id -g $USER` \
                    make_asset_dataset
