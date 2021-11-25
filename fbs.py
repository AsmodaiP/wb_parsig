import os
import json 

if __name__ == '__main__':
    data = json.load(open('result.json', 'rb'))
    print(data)