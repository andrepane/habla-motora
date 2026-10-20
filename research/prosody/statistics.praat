form Independent native queries on centre-restricted Pitch objects
 sentence Jobs_file
 sentence Output_folder
endform
Read Strings from raw text file: jobs_file$
jobs = selected("Strings")
n = Get number of strings
for i from 1 to n
 selectObject: jobs
 ident$ = Get string: i
 Read from file: output_folder$ + "/" + ident$ + ".selected.Pitch"
 pitch = selected("Pitch")
 mean = Get mean: 0, 0, "Hertz"
 sd = Get standard deviation: 0, 0, "Hertz"
 sdST = Get standard deviation: 0, 0, "semitones"
 median = Get quantile: 0, 0, 0.5, "Hertz"
 p10 = Get quantile: 0, 0, 0.1, "Hertz"
 p90 = Get quantile: 0, 0, 0.9, "Hertz"
 minimum = Get minimum: 0, 0, "Hertz", "None"
 maximum = Get maximum: 0, 0, "Hertz", "None"
 writeFileLine: output_folder$ + "/" + ident$ + ".stats", mean, tab$, median, tab$, sd, tab$, sdST, tab$, p10, tab$, p90, tab$, minimum, tab$, maximum
 removeObject: pitch
endfor
