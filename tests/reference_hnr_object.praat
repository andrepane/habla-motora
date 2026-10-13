form Controlled native Harmonicity
    sentence Matrix_file
    real Start
    real End
endform
Read from file: matrix_file$
To Harmonicity
m = Get mean: start,end
m$ = "null"
if m <> undefined
    m$ = fixed$(m,17)
endif
writeInfoLine: "{""hnr_mean_db"":",m$,"}"
