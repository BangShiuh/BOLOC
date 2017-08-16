import parser

with open('bolsigdb.dat') as fp:
    processes = parser.parse(fp)
    #excitation = parser._read_excitation(fp)

#excitation = parser._read_excitation(processes)
#print(processes)