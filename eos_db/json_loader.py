#!/usr/bin/python
#Also works for Python3

import json
from warnings import warn

def parse_json_file(filename):

    with open(filename) as f:
        return parse_json_fh(f)

def parse_json_fh(f):
    """ Parse a JSON file
        First remove comments and then use the json module package
        Comments look like :
            // ...
        or
            /*
            ...
            */

        This is based on
        http://www.lifl.fr/~damien.riquet/parse-a-json-file-with-comments.html
        but eschews regexes and also handles comments embedded in strings.
        For some reason it also handles single quoted strings even though these
        are totally invalid JSON.  A warning will be issued if one is spotted.
    """
    sq_seen = False

    #Buffer for processed content
    content = []

    NORMAL = 0
    IN_COMMENT = 1
    IN_DQ_STR = 2
    IN_SQ_STR = 3

    mode = 0

    for l in f.readlines():

        #we're reading along the lines, and on finding a comment we
        #print out what we have so far then scan to the end and set the mark and
        #then repeat the process.
        #This strategy is ok for our purposes.  To do any more you'd want a
        #proper parsing strategy.
        skip = 0
        mark = 0

        for i, c in enumerate(l):

            if skip:
                skip -= 1
                continue

            #Look for the chars we care about: / " ' \ *
            if mode == NORMAL:
                if(c == "/" and l[i+1] == "/"):
                    content.append(l[mark:i] + "\n")
                    break
                elif(c == "/" and l[i+1] == "*"):
                    mode = IN_COMMENT
                    skip = 1
                    content.append(l[mark:i])
                elif(c == "'"):
                    mode = IN_SQ_STR
                    if not sq_seen:
                        warn("Encountered illegal single quoted string. JSON will not parse.")
                        sq_seen = 0
                elif(c == '"'):
                    mode = IN_DQ_STR
            elif mode == IN_COMMENT:
                if(c == "*" and l[i+1] == "/"):
                    mark = i+2
                    skip = 1
                    mode = NORMAL
            elif mode == IN_SQ_STR:
                if(c == '\\'):
                    skip = 1
                elif(c == "'"):
                    mode = NORMAL
            elif mode == IN_DQ_STR:
                if(c == '\\'):
                    skip = 1
                elif(c == '"'):
                    mode = NORMAL
        else:
            if mode != IN_COMMENT:
                content.append(l[mark:])

    content = ''.join(content)

    #For debugging
    #print(content)

    # Return json file
    return json.loads(content)

if __name__ == "__main__":
    #This only works on Linux
    foo = parse_json_file("/dev/stdin")
    print(foo)
