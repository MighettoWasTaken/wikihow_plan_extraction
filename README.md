### test.py requires: 

1. csv named 'webextractdata.csv' 

this file contains: "file,url,time,goal,steps,index\n" before you run the code. 

2. txt named 'index.txt' 

this file contains: starting index for parsing. 26 default as all indexes before 26 are catagory pages, which are not useful. 

3. Offline wikihow with scraped wikihow hmtl's 

Adjust filenames in extractor.py as needed

### How to use: 

Once all necesary files are aquired, run 

```
python extractor.py
```

### Package versions: 

pandas                   2.0.1

requests-html            0.10.0

requests                 2.30.0

absl-py                  1.4.0

bs4                      0.0.1

