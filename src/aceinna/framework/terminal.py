# inspire from https://github.com/wong2/pick/blob/master/pick/__init__.py
import curses
import sys

KEYS_ENTER = (curses.KEY_ENTER, ord('\n'), ord('\r'))
KEYS_UP = (curses.KEY_UP, ord('k'))
KEYS_DOWN = (curses.KEY_DOWN, ord('j'))
KEYS_SELECT = (curses.KEY_RIGHT, ord(' '))

# class Fore(object):
#     red = code_to_chars(31)
#     green = code_to_chars(32)
#     yellow = code_to_chars(33)
#     blue = code_to_chars(34)


class Choice(object):
    def __init__(self, title=None, options=[], indicator='>', default_index=0):
        self.options = options
        self.title = title
        self.indicator = indicator

        if default_index >= len(options):
            raise ValueError(
                'default_index should be less than the length of options')

        self.index = default_index

    def move_up(self):
        self.index -= 1
        if self.index < 0:
            self.index = len(self.options) - 1

    def move_down(self):
        self.index += 1
        if self.index >= len(self.options):
            self.index = 0

    def get_selected(self):
        """return the current selected option as a tuple: (option, index)
           or as a list of tuples (in case multiselect==True)
        """
        return self.index, self.options[self.index]

    def get_title_lines(self):
        if self.title:
            return self.title.split('\n') + ['']
        return []

    def get_option_lines(self):
        lines = []
        for index, option in enumerate(self.options):
            # pass the option through the options map of one was passed in
            if index == self.index:
                prefix = self.indicator
                format = curses.color_pair(1)
                line = ('{0} {1}'.format(prefix, option), format)
            else:
                prefix = len(self.indicator) * ' '
                line = '{0} {1}'.format(prefix, option)

            lines.append(line)

        return lines

    def get_lines(self):
        title_lines = self.get_title_lines()
        option_lines = self.get_option_lines()
        lines = title_lines + option_lines
        current_line = self.index + len(title_lines) + 1
        return lines, current_line

    def draw(self):
        """draw the curses ui on the screen, handle scroll if needed"""
        self.screen.clear()

        x, y = 1, 1  # start point
        max_y, max_x = self.screen.getmaxyx()
        max_rows = max_y - y  # the max rows we can draw

        lines, current_line = self.get_lines()

        # calculate how many lines we should scroll, relative to the top
        scroll_top = getattr(self, 'scroll_top', 0)
        if current_line <= scroll_top:
            scroll_top = 0
        elif current_line - scroll_top > max_rows:
            scroll_top = current_line - max_rows
        self.scroll_top = scroll_top

        lines_to_draw = lines[scroll_top:scroll_top + max_rows]

        for line in lines_to_draw:
            if type(line) is tuple:
                self.screen.addnstr(y, x, line[0], max_x - 2, line[1])
            else:
                self.screen.addnstr(y, x, line, max_x - 2)
            y += 1

        self.screen.refresh()

    def run_loop(self):
        while True:
            self.draw()
            c = self.screen.getch()
            if c in KEYS_UP:
                self.move_up()
            elif c in KEYS_DOWN:
                self.move_down()
            elif c in KEYS_ENTER:
                return self.get_selected()

    def config_curses(self):
        try:
            # use the default colors of the terminal
            curses.use_default_colors()
            # hide the cursor
            curses.curs_set(0)
            # add some color for multi_select
            # @todo make colors configurable
            curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        except:
            # Curses failed to initialize color support, eg. when TERM=vt100
            curses.initscr()

    def _start(self, screen):
        self.screen = screen
        self.config_curses()
        return self.run_loop()

    def get_choice(self):
        return curses.wrapper(self._start)
        return self.run_loop()
