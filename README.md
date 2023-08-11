# Mypy-ind

Mypyind is a tool to find all the occurances of given function call.

# Usage

1. Install required dependencies of mypy.
`pip install -r mypy-requirements.txt`
`pip install -e .`
2. Add the fullpath of function in `mypyind/data/seed.txt`
3. then call mypyind to a target directory, then mypyind will iteratively find all occurrences.
`python mypyind {target_directory}`
4. The result will be stored in files listed below.
   1. `mypyind/data/found.txt` : All unique function fullnames that are found
   2. `mypyind/data/found.log` : Iteration logs
   3. `mypyind/data/found.json` : JSON representation of found.log

# Naming

To honor original writers of mypy, Mypy(-)ind is a combination of mypy and find.
