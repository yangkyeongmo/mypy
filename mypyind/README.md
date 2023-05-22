# Mypy-ind

Mypy(-)ind is a combination of mypy and find.
It is a tool to find all the occurances of given function call.
It has mypy as prefix since this project is based on mypy.
All credits to mypy developers!

# Usage

1. Install required dependencies of mypy.
`pip install -r mypy-requirements.txt`
`pip install -e .`
2. Add the fullpath of function in `fullnames.txt` or `members.txt`.
3. then call mypyind to a target directory, then mypyind will iteratively find all occurances.
`python mypyind {target_directory}`
