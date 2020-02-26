import sys
try:
    from aceinna.bootstrap.cli import CommandLine
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.bootstrap.cli import CommandLine


def main():
    '''start'''
    command_line = CommandLine()
    command_line.listen()


if __name__ == '__main__':
    main()
