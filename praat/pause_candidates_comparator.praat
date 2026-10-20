form Offline intensity comparator
    sentence Input_file
    real Start_s 0
    real End_s 1
endform
Read from file: input_file$
Extract part: start_s, end_s, "rectangular", 1, "no"
To TextGrid (silences): 100, 0.005, -18, 0.08, 0.000001, "candidate", "activity"
n = Get number of intervals: 1
for i from 1 to n
    label$ = Get label of interval: 1, i
    if label$ = "candidate"
        a = Get start time of interval: 1, i
        b = Get end time of interval: 1, i
        appendInfoLine: fixed$(a, 12), " ", fixed$(b, 12)
    endif
endfor
