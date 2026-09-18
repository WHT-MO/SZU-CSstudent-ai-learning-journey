#print(os.getcwd())
#NameError: name 'os' is not defined
import os
print(os.getcwd())
#D:\code\dsh\python-course\code\L12
import sys
print(sys.version)
print(sys.executable)
import math
#print(sqrt(9))
#NameError: name 'sqrt' is not defined
print(math.sqrt(9))
print(os.environ["PATH"].split(";"))
print(__file__)
print(os.path.dirname(__file__))