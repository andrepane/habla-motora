form Duration smoke test
    sentence Input_file
endform
Read from file: input_file$
duration = Get total duration
writeInfoLine: fixed$(duration, 12)
