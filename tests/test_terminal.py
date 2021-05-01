import sys
try:
    from aceinna.framework.terminal import Choice
except:  # pylint: disable=bare-except
    print('load package from local')
    sys.path.append('./src')
    from aceinna.framework.terminal import Choice

def test_choice():
    c = Choice(
            title='New version {0} is prepared, continue to update?'.format(
            '2.2.0'), 
            options=['Yes', 'No', 'Skip this version'])

    choice = c.get_choice()
    if choice:
        index, _ = choice
    print(choice)

if __name__ == '__main__':
    test_choice()