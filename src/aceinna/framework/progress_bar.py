import sys


class ProgressBar():
    """
    Display progress bar
    """
    current = 0  # current step
    max_steps = 0  # total steps
    max_arrow = 50  # length of progress bar
    done_info = 'done'

    def __init__(self, total, done_info='Done'):
        self.max_steps = total
        self.i = 0
        self.done_info = done_info

    # [>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>]100.00%
    def update(self, i=None):
        '''update the progress display
        '''
        if i is not None:
            self.i += i
        else:
            self.i += 1
        # caculate the number of '>'
        num_arrow = int(self.i * self.max_arrow / self.max_steps)
        num_line = self.max_arrow - num_arrow  # caculate the number of '-'
        percent = self.i * 100.0 / self.max_steps  # caculate the percent
        process_bar = '[' + '>' * num_arrow + '-' * num_line + ']'\
                      + '%.2f' % percent + '%' + '\r'
        sys.stdout.write(process_bar)  # print info on terminal
        sys.stdout.flush()
        if self.i >= self.max_steps:
            self.close(True)

    def close(self, print_done_info=False):
        '''close print
        '''
        if print_done_info:
            print(self.done_info)
        self.i = 0
