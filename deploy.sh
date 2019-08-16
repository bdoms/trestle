#!/bin/bash

poetry install

# uncomment these lines if you're using svelte
# yarn install
# yarn build

service supervisor restart

# only need to restart nginx if config has changed
# service nginx restart
