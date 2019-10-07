#!/bin/bash

docker build -t make_asset_dataset .
docker run -it --rm -v /research/irates/data/raw/bloomberg:/app/bloomberg \
                    -v /research/irates/data/processed:/app/output \
                    -u `id -u $USER`:`id -g $USER` \
                    make_asset_dataset /bin/bash