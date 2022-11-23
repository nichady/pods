# pods

Pods is a python script to spin up a podman stack.

## Commands

`./pods.py up [podname]`
`./pods.py down [podname]`
`./pods.py restart [podname]`

## Configuration

`pods.toml` is the configuration file; it will load files from the `pods/` directory.
A `.env` file will also be used to pass environment variables. Environment variables
will replace text in the format of "${VARNAME}" in the pod files.

