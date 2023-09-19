from scratch_task_by_category import extract_wikihow
import pandas as pd 
import pathlib
from csv import writer

root = pathlib.Path("offline_wikihow/wikihow_archive")

csvfile = pd.read_csv(root.joinpath('wikihow_archive.csv'))
keys = ["file","url","time"]

#first working index: 26
index_file = open('index.txt', 'r')
dataset_file = open('webextractdata.csv', 'a', encoding="utf-8", newline='')
start_index = int(index_file.read())
index_file.close()

writer_object = writer(dataset_file)

#print(len(csvfile))

dataset = []
for file_index in range(start_index, 50): #len(csvfile) 
    html = open(root.joinpath(csvfile[keys[0]][file_index]), encoding='utf8')
    raw = extract_wikihow(csvfile[keys[1]][file_index], html)
    for item in raw: 
        #[file, url, time, goal, steps]
        
        if len(item[1]) != 0:
            writer_object.writerow([csvfile[keys[0]][file_index], csvfile[keys[1]][file_index], csvfile[keys[2]][file_index], item[0].replace("\\n", ""), item[1]])
    html.close() 
    index_file = open('index.txt', 'w')
    index_file.write(str(file_index+1))
    index_file.close() 

dataset_file.close()
#print(csvfile[keys[1]][file_index])
#print(process_html(csvfile[keys[1]][file_index], html))
