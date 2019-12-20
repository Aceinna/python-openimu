import sys
try:
    from openimu.commands import OpenIMU_CLI
except:
    print('load openimu from parent path')
    sys.path.append('.')
    from openimu.commands import OpenIMU_CLI

if __name__ == "__main__":
    cli = OpenIMU_CLI()
    cli.connect_handler()
    cli.command_handler()
