form Independent native HNR query
    sentence Input_file
    real Start
    real End
endform
Read from file: input_file$
To Harmonicity (cc): 0.01,75,0.1,4.5
m = Get mean: start,end
m$ = "null"
if m <> undefined
    m$ = fixed$(m,17)
endif
n = Get number of frames
writeInfo: "{""hnr_mean_db"":",m$,",""frames"": ["
separator$ = ""
for i from 1 to n
    t = Get time from frame number: i
    if t >= start and t <= end
        v = Get value in frame: i
        v$ = "null"
        if v <> undefined
            v$ = fixed$(v,17)
        endif
        appendInfo: separator$, "{""frame_index"":",i,",""time_s"":",fixed$(t,17),",""praat_raw_hnr_db"":",v$,"}"
        separator$ = ","
    endif
endfor
appendInfoLine: "]}"
