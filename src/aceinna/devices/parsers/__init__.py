import math
def filter_nan(value):
    '''
    Filter NaN
    '''
    if not isinstance(value, float):
        return value

    if math.isnan(value):
        return 0
    else:
        return value