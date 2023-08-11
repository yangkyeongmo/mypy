# Mypy-ind

Mypyind is a tool to find all the occurrences of given function call, based on [mypy](https://github.com/python/mypy).

# Usage

1. Install required dependencies of mypy.
```sh
pip install -r mypy-requirements.txt`
pip install -e .
```
2. Add the fullpath of function in `mypyind/data/seed.txt`
3. then call mypyind to a target directory, then mypyind will iteratively find all occurrences.
```sh
python mypyind {target_directory}
```
4. The result will be stored in files listed below.
   1. `mypyind/data/found.txt` : All unique function fullnames that are found
   2. `mypyind/data/found.log` : Iteration logs
   3. `mypyind/data/found.json` : JSON representation of found.log

## Example

Example seed is given in `mypyind/data/seed.txt`. It contains `mypy.build.order_ascc`.

If you run `python mypyind ./mypy`, then mypyind will try to find all function call to `mypy.build.order_ascc` in `mypy` directory.

The example result is given in `mypyind/data/found.txt`, `mypyind/data/found.log` and `mypyind/data/found.json`.

# Representation of result files

## found.txt

Each line of `found.txt` contains a fullname of function call that is found.

## found.log

Each line of `found.log` contains a fullname of function call that is found, and the fullname of function that calls it.

```log
[Iteration Number] [Fullname of function call] is called from [Fullname of function that calls it]
```

## found.json

`found.json` is a re-rendered JSON representation of `found.log`.

If a function call has caller, it's items have caller's fullname as key and number of iteration when it was found as value.
```
{
    "Fullname of function call": {
        "Fullname of function that calls the function": Iteration Numer,
        ...
    }
}
```

# How it works

At first iteration, mypyind will find all the function call to `mypy.build.order_ascc` in `mypy` directory, and store the result in result files.
Then, mypyind will find all the function call to found functions, and store the result in result files.
This process will be repeated until no new function call is found.

# Limitation

Since this tool is based on mypy, it has same limitation with mypy.
Other than that, since mypy is static type checker, it cannot find function call that is dynamically generated.

# Naming

To honor original writers of mypy, Mypy(-)ind is a combination of mypy and find.
