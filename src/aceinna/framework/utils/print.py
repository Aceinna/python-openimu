import platform

if 'Windows' in platform.system():
    import sys
    import ctypes
    __std_input_handle = -10
    __std_output_handle = -11
    __std_error_handle = -12
    __fore_ground_BLUE = 0x09
    __fore_ground_GREEN = 0x0a
    __fore_ground_RED = 0x0c
    __fore_ground_YELLOW = 0x0e
    std_out_handle = ctypes.windll.kernel32.GetStdHandle(__std_output_handle)

    def set_cmd_color(color, handle=std_out_handle):
        return ctypes.windll.kernel32.SetConsoleTextAttribute(handle, color)

    def reset_cmd_color():
        set_cmd_color(__fore_ground_RED | __fore_ground_GREEN | __fore_ground_BLUE)

    def print_blue(msg):
        set_cmd_color(__fore_ground_BLUE)
        sys.stdout.write(msg + '\n')
        reset_cmd_color()

    def print_green(msg):
        set_cmd_color(__fore_ground_GREEN)
        sys.stdout.write(msg + '\n')
        reset_cmd_color()

    def print_red(msg):
        set_cmd_color(__fore_ground_RED)
        sys.stdout.write(msg + '\n')
        reset_cmd_color()

    def print_yellow(msg):
        set_cmd_color(__fore_ground_YELLOW)
        sys.stdout.write(msg + '\n')
        reset_cmd_color()
else:
    STYLE = {
        'fore': {
            'red': 31,
            'green': 32,
            'yellow': 33,
            'blue': 34
        }
    }

    def use_style(msg, mode='', fore='', back='40'):
        fore = '%s' % STYLE['fore'][fore] if STYLE['fore'].__contains__(
            fore) else ''
        style = ';'.join([s for s in [mode, fore, back] if s])
        style = '\033[%sm' % style if style else ''
        end = '\033[%sm' % 0 if style else ''
        return '%s%s%s' % (style, msg, end)

    def print_red(msg):
        print(use_style(msg, fore='red'))

    def print_green(msg):
        print(use_style(msg, fore='green'))

    def print_yellow(msg):
        print(use_style(msg, fore='yellow'))

    def print_blue(msg):
        print(use_style(msg, fore='blue'))
