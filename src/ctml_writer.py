import parser

with open('bolsigdb.dat') as fp:
    processes = parser.parse(fp)

