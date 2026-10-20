form Batch extraction; no statistics on exterior frames
 sentence Input_file
 sentence Jobs_file
 sentence Output_folder
endform
Read from file: input_file$
sound = selected("Sound")
Read Table from tab-separated file: jobs_file$
jobs = selected("Table")
n = Get number of rows
for row from 1 to n
 selectObject: jobs
 ident$ = Get value: row, "id"
 method$ = Get value: row, "method"
 floor = Get value: row, "floor"
 top = Get value: row, "top"
 silence = Get value: row, "silence"
 voicing = Get value: row, "voicing"
 cost = Get value: row, "cost"
 left = Get value: row, "left"
 right = Get value: row, "right"
 selectObject: sound
 Extract part: left, right, "rectangular", 1, "yes"
 part = selected("Sound")
 if method$ = "filtered autocorrelation"
  To Pitch (filtered autocorrelation): 0.005, floor, top, 15, "no", 0.03, silence, voicing, cost, 0.35, 0.14
 elsif method$ = "raw autocorrelation"
  To Pitch (raw autocorrelation): 0.005, floor, top, 15, "no", silence, voicing, cost, 0.35, 0.14
 else
  To Pitch (raw cross-correlation): 0.005, floor, top, 15, "no", silence, voicing, cost, 0.35, 0.14
 endif
 pitch = selected("Pitch")
 Save as short text file: output_folder$ + "/" + ident$ + ".Pitch"
 removeObject: pitch, part
endfor
