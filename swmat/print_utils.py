import json

GREEN = "\033[1;32m"
RED   = "\033[31m"
BLUE  = "\033[1;34m"
RESET = "\033[0m"

def print_colored(pin, end=None):
    if pin:
        print (GREEN + f"{pin}" + RESET, end=' ')
    else:
        print (RED   + f"{pin}" + RESET, end=' ');

def print_with_frame(pins, ch=None, frame=True, colored=True, cols=16):
    noheadflg  = True
    noprintflg = True
    
    for i, pin in enumerate(pins):
        if (ch is not None) and (i//cols not in ch): 
            continue

        if (noheadflg and frame):
            print (' '*3+'| ', end='')

            for j in range(cols):
                print (f"{j:2d} ", end='')

            print ('\n'+'-'*53)
            noheadflg = False

        if i%cols == 0 and frame:
            print (f"{i//16:2d} |  ", end='')

        if colored:
            print_colored(pin, end='')
        else: 
            print (f"{pin} ", end='')

        if frame: print (end=' ')

        noprintflg = False

        if i%cols == cols - 1:
            print ()

    if (noprintflg):
        print ("The pcfid out of range.")

def parse_first_json_line(text: str):
    for line in text.splitlines():
        line = line.strip()
        if line.startswith('{') and line.endswith('}'):
            return json.loads(line)
    raise ValueError("No JSON line found in response")


