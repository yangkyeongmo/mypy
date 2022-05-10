import os


TXTFILE = 'fullnames.txt'
TXT_DEBUG_FILE = 'fullnames_debug.txt'


def main():
    fullnames = set(open(TXTFILE, 'r').readlines())
    i = 0
    debug_write_level(i)
    print(f'{i=}')
    cmd = 'python __main__.py ~/Projects/third_party/mypy/mypy --cache-dir=/dev/null --ignore-missing-imports'
    os.system(cmd)

    new_fullnames = set(open(TXTFILE, 'r').readlines())
    while fullnames != new_fullnames:
        i += 1
        debug_write_level(i)
        print(f'{i=}')
        os.system(cmd)
        fullnames = new_fullnames
        new_fullnames = set(open(TXTFILE, 'r').readlines())


def debug_write_level(level):
    with open(TXT_DEBUG_FILE, 'a') as f:
        f.write(f'{level=}\n')


if __name__ == '__main__':
    main()
